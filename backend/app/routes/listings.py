from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..models import Listing, ListingImage
from ..image_uploads import save_listing_images, MAX_IMAGES_PER_LISTING

router = APIRouter(
    prefix="/listings",
    tags=["listings"]
)

# Pydantic schemas for request/response
class ListingBase(BaseModel):
    title: str
    location: str
    area: float
    property_type: str
    price: float
    bedrooms: int
    bathrooms: int
    status: str = "available"

class ListingCreate(ListingBase):
    pass

class ListingUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    area: Optional[float] = None
    property_type: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    status: Optional[str] = None

class ListingResponse(ListingBase):
    id: int
    is_sold: bool = False
    # Added in image-upload feature: list of public image URLs.
    # Empty list when the listing has no images. Existing fields are unchanged.
    images: List[str] = []

    class Config:
        orm_mode = True


class ListingDetailResponse(ListingResponse):
    """Detail-page response. Adds submitter fields — these are PII and are
    exposed ONLY on the singular detail endpoint, never on the list endpoint.
    """
    submitter_name: Optional[str] = None
    submitter_contact: Optional[str] = None


def _listing_to_dict(listing: Listing) -> dict:
    """Serialize a Listing ORM object to the public response shape.

    Includes the new `images` list. Existing fields are preserved exactly.
    NOTE: Intentionally EXCLUDES submitter_name and submitter_contact. Those
    fields are PII and must never appear on the public list endpoint. They
    live only on the singular detail endpoint — see _listing_detail_to_dict.
    """
    return {
        "id": listing.id,
        "title": listing.title,
        "location": listing.location,
        "area": listing.area,
        "property_type": listing.property_type,
        "price": listing.price,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "status": listing.status,
        "is_sold": getattr(listing, "is_sold", False) or False,
        "images": [img.image_path for img in (listing.images or [])],
    }


def _listing_detail_to_dict(listing: Listing) -> dict:
    """Detail-page serialization.

    Same as the public list shape, PLUS submitter_name and submitter_contact
    so the detail page can show a "Contact Submitter" section. This is the
    ONLY endpoint where those fields are exposed — the list endpoint strips
    them via _listing_to_dict.
    """
    base = _listing_to_dict(listing)
    base["submitter_name"] = listing.submitter_name
    base["submitter_contact"] = listing.submitter_contact
    return base


@router.post("/submit", response_model=ListingResponse)
def submit_listing(
    title: str = Form(...),
    location: str = Form(...),
    area: float = Form(...),
    property_type: str = Form(...),
    price: float = Form(...),
    bedrooms: int = Form(...),
    bathrooms: int = Form(...),
    submitter_name: str = Form(...),
    submitter_contact: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """Public endpoint — accepts user-submitted listings as pending.

    Now accepts multipart/form-data so clients can attach up to 5 images.
    """
    # 1) Validate + save images FIRST (before any DB writes), so a
    #    validation failure leaves no half-submitted listing behind.
    image_urls = save_listing_images(images or [])

    db_listing = Listing(
        title=title,
        location=location,
        area=area,
        property_type=property_type,
        price=price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        status="pending",
        submitter_name=submitter_name,
        submitter_contact=submitter_contact,
    )
    db.add(db_listing)
    db.flush()  # populate db_listing.id without committing yet

    for url in image_urls:
        db.add(ListingImage(listing_id=db_listing.id, image_path=url))

    db.commit()
    db.refresh(db_listing)
    return _listing_to_dict(db_listing)


@router.post("/", response_model=ListingResponse)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return _listing_to_dict(db_listing)


@router.get("/", response_model=List[ListingResponse])
def read_listings(db: Session = Depends(get_db)):
    # Public view: only show listings that have been approved for publication.
    # Treat legacy "available" rows as approved so existing admin-created rows
    # remain visible after the model default switch.
    # NOTE: Soft-deleted listings (status="deleted") MUST never appear here —
    # they are explicitly excluded by the approved/available allow-list below.
    listings = (
        db.query(Listing)
        .filter(Listing.status.in_(["approved", "available"]))
        .all()
    )
    # Eagerly load images via the relationship. SQLAlchemy lazy-loads them
    # when we touch listing.images in _listing_to_dict, which is fine.
    return [_listing_to_dict(lst) for lst in listings]


@router.get("/{id}", response_model=ListingDetailResponse)
def read_listing(id: int, db: Session = Depends(get_db)):
    """Single-listing detail endpoint.

    Only approved (or legacy 'available') listings are reachable here.
    Pending, rejected, and soft-deleted rows all return 404 — same response
    as a truly nonexistent row, so callers cannot probe for hidden listings
    by ID. Returns the detail shape (includes submitter fields).
    """
    db_listing = (
        db.query(Listing)
        .filter(Listing.id == id)
        .filter(Listing.status.in_(["approved", "available"]))
        .first()
    )
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_detail_to_dict(db_listing)


@router.put("/{id}", response_model=ListingResponse)
def update_listing(id: int, listing_update: ListingUpdate, db: Session = Depends(get_db)):
    db_listing = db.query(Listing).filter(Listing.id == id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    update_data = listing_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_listing, key, value)

    db.commit()
    db.refresh(db_listing)
    return _listing_to_dict(db_listing)


@router.delete("/{id}")
def delete_listing(id: int, db: Session = Depends(get_db)):
    db_listing = db.query(Listing).filter(Listing.id == id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    db.delete(db_listing)
    db.commit()
    return {"detail": "Listing deleted successfully"}
