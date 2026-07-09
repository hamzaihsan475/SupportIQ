from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from collections import defaultdict
from typing import List

from backend.app.auth import verify_admin_credentials
from backend.app.database import get_db
from backend.app.models import Listing, ListingImage, Lead, Conversation
from backend.app.image_uploads import save_listing_images

# Every route registered on this router requires HTTP Basic Auth — see
# backend/app/auth.py. Applied at the router level so individual route
# handlers stay focused on business logic.
router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(verify_admin_credentials)],
)


def _listing_to_dict(listing: Listing) -> dict:
    """Serialize a Listing ORM object to the admin response shape.

    Mirrors the public /listings shape, including the new `images` list.
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
        "agency_id": listing.agency_id,
        "submitter_name": listing.submitter_name,
        "submitter_contact": listing.submitter_contact,
        "is_sold": listing.is_sold,
        "images": [img.image_path for img in (listing.images or [])],
    }


@router.get("/listings")
async def get_admin_listings(db: Session = Depends(get_db)):
    """Retrieve all property listings for admin view."""
    listings = db.query(Listing).all()
    return [_listing_to_dict(lst) for lst in listings]


@router.post("/listings")
async def create_listing(
    title: str = Form(...),
    location: str = Form(...),
    area: float = Form(...),
    property_type: str = Form(...),
    price: float = Form(...),
    bedrooms: int = Form(...),
    bathrooms: int = Form(...),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """Create a new property listing. Optional image attachments (up to 5)."""
    # Validate + save images first; on failure nothing is committed.
    image_urls = save_listing_images(images or [])

    try:
        new_listing = Listing(
            title=title,
            location=location,
            area=area,
            property_type=property_type,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            # Admin-created listings are visible immediately.
            status="approved",
        )
        db.add(new_listing)
        db.flush()

        for url in image_urls:
            db.add(ListingImage(listing_id=new_listing.id, image_path=url))

        db.commit()
        db.refresh(new_listing)
        return _listing_to_dict(new_listing)
    except HTTPException:
        # Validation error from save_listing_images — re-raise as-is.
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating listing: {str(e)}")


@router.post("/listings/{listing_id}/approve")
async def approve_listing(listing_id: int, db: Session = Depends(get_db)):
    """Approve a user-submitted listing so it becomes publicly visible."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "approved"
    db.commit()
    db.refresh(listing)
    return {"status": "approved", "listing_id": listing_id}


@router.post("/listings/{listing_id}/reject")
async def reject_listing(listing_id: int, db: Session = Depends(get_db)):
    """Reject a user-submitted listing. Row is preserved for audit."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "rejected"
    db.commit()
    db.refresh(listing)
    return {"status": "rejected", "listing_id": listing_id}


@router.post("/listings/{listing_id}/delete")
async def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    """Soft-delete a listing by setting status to 'deleted'. Row is preserved."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "deleted"
    db.commit()
    db.refresh(listing)
    return {"status": "deleted", "listing_id": listing_id}


@router.post("/listings/{listing_id}/mark-sold")
async def mark_listing_sold(listing_id: int, db: Session = Depends(get_db)):
    """Mark a listing as sold. Row remains visible on the public page with a SOLD badge."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.is_sold = True
    db.commit()
    db.refresh(listing)
    return {"is_sold": True, "listing_id": listing_id}


@router.post("/listings/{listing_id}/mark-unsold")
async def mark_listing_unsold(listing_id: int, db: Session = Depends(get_db)):
    """Undo a sold mark on a listing."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.is_sold = False
    db.commit()
    db.refresh(listing)
    return {"is_sold": False, "listing_id": listing_id}


@router.get("/leads")
async def get_admin_leads(db: Session = Depends(get_db)):
    """Retrieve all captured user leads for admin view."""
    return db.query(Lead).all()


@router.get("/conversations")
async def get_admin_conversations(db: Session = Depends(get_db)):
    """Retrieve all chatbot interaction logs grouped by session_id."""
    convs = db.query(Conversation).all()

    # Group conversations by session_id
    grouped = defaultdict(list)
    for c in convs:
        grouped[c.session_id].append({
            "role": c.role,
            "message": c.message,
            "created_at": c.created_at
        })

    return grouped


@router.get("/escalated")
async def get_escalated_conversations(db: Session = Depends(get_db)):
    """Retrieve all escalated conversations grouped by session_id."""
    convs = db.query(Conversation).filter(Conversation.status == "escalated").all()

    grouped = defaultdict(list)
    for c in convs:
        grouped[c.session_id].append({
            "role": c.role,
            "message": c.message,
            "created_at": c.created_at
        })

    return grouped


@router.post("/resolve/{session_id}")
async def resolve_conversation(session_id: str, db: Session = Depends(get_db)):
    """Mark all conversations in a session as resolved."""
    db.query(Conversation).filter(Conversation.session_id == session_id).update({"status": "resolved"})
    db.commit()
    return {"message": f"Session {session_id} marked as resolved"}


@router.post("/send-message")
async def send_admin_message(data: dict[str, str], db: Session = Depends(get_db)):
    """Send a message from admin to user."""
    session_id = data.get("session_id")
    message_text = data.get("message_text")

    if not session_id or not message_text:
        raise HTTPException(status_code=400, detail="session_id and message_text are required")

    admin_conv = Conversation(
        session_id=session_id,
        role="bot",
        message=message_text,
        status="escalated"
    )
    db.add(admin_conv)
    db.commit()
    return {"status": "sent", "session_id": session_id}


@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """Compute and return aggregated system metrics."""
    total_listings = db.query(Listing).count()
    total_leads = db.query(Lead).count()
    total_messages = db.query(Conversation).count()
    unique_sessions = db.query(Conversation.session_id).distinct().count()

    return {
        "total_listings": total_listings,
        "total_leads": total_leads,
        "total_messages": total_messages,
        "unique_sessions": unique_sessions
    }
