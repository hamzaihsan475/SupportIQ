from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from collections import defaultdict
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models import Listing, Lead, Conversation

router = APIRouter(tags=["admin"])

class ListingCreate(BaseModel):
    title: str
    location: str
    area: float
    property_type: str
    price: float
    bedrooms: int
    bathrooms: int

@router.get("/listings")
async def get_admin_listings(db: Session = Depends(get_db)):
    """Retrieve all property listings for admin view."""
    return db.query(Listing).all()

@router.post("/listings")
async def create_listing(listing: ListingCreate, db: Session = Depends(get_db)):
    """Create a new property listing."""
    try:
        new_listing = Listing(
            title=listing.title,
            location=listing.location,
            area=listing.area,
            property_type=listing.property_type,
            price=listing.price,
            bedrooms=listing.bedrooms,
            bathrooms=listing.bathrooms
        )
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        return new_listing
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating listing: {str(e)}")

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
