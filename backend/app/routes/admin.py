from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Listing, Lead, Conversation

router = APIRouter()

@router.get("/listings")
def get_listings(db: Session = Depends(get_db)):
    listings = db.query(Listing).all()
    return listings

@router.get("/leads")
def get_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return leads

@router.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    messages = db.query(Conversation).order_by(Conversation.created_at.asc()).all()

    sessions = {}
    for msg in messages:
        if msg.session_id not in sessions:
            sessions[msg.session_id] = []
        sessions[msg.session_id].append({
            "role": msg.role,
            "message": msg.message,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        })

    return [
        {"session_id": sid, "messages": msgs}
        for sid, msgs in sessions.items()
    ]

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_listings = db.query(Listing).count()
    total_leads = db.query(Lead).count()
    total_conversations = db.query(Conversation).count()
    unique_sessions = db.query(Conversation.session_id).distinct().count()

    return {
        "total_listings": total_listings,
        "total_leads": total_leads,
        "total_conversations": total_conversations,
        "unique_sessions": unique_sessions
    }
