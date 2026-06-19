from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import Listing

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

    class Config:
        orm_mode = True

class ListingSubmit(BaseModel):
    title: str
    location: str
    area: float
    property_type: str
    price: float
    bedrooms: int
    bathrooms: int
    submitter_name: str
    submitter_contact: str

@router.post("/submit", response_model=ListingResponse)
def submit_listing(payload: ListingSubmit, db: Session = Depends(get_db)):
    """Public endpoint — accepts user-submitted listings as pending."""
    data = payload.dict()
    submitter_name = data.pop("submitter_name")
    submitter_contact = data.pop("submitter_contact")

    db_listing = Listing(
        **data,
        status="pending",
        submitter_name=submitter_name,
        submitter_contact=submitter_contact,
    )
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@router.post("/", response_model=ListingResponse)
def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    db_listing = Listing(**listing.dict())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

@router.get("/", response_model=List[ListingResponse])
def read_listings(db: Session = Depends(get_db)):
    # Public view: only show listings that have been approved for publication.
    # Treat legacy "available" rows as approved so existing admin-created rows
    # remain visible after the model default switch.
    listings = (
        db.query(Listing)
        .filter(Listing.status.in_(["approved", "available"]))
        .all()
    )
    return listings

@router.get("/{id}", response_model=ListingResponse)
def read_listing(id: int, db: Session = Depends(get_db)):
    db_listing = db.query(Listing).filter(Listing.id == id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return db_listing

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
    return db_listing

@router.delete("/{id}")
def delete_listing(id: int, db: Session = Depends(get_db)):
    db_listing = db.query(Listing).filter(Listing.id == id).first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    db.delete(db_listing)
    db.commit()
    return {"detail": "Listing deleted successfully"}
