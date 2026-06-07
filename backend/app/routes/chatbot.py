from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models import Lead, Conversation
from backend.app.ml.classifier import predict_intent
from backend.app.ml.rag import get_rag_response

router = APIRouter()

# In-memory session store to manage conversation state and temporary lead data
# Structure: { session_id: { "state": str, "lead_data": dict } }
SESSION_STORE: dict[str, dict[str, Any]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    user_msg = request.message
    session_id = request.session_id

    # Check if session is already escalated
    escalated_session = db.query(Conversation).filter(Conversation.session_id == session_id, Conversation.status == "escalated").first()
    if escalated_session:
        # BYPASS AI: Log user message and return a system signal for the frontend
        user_conv = Conversation(session_id=session_id, role="user", message=user_msg, status="escalated")
        db.add(user_conv)
        db.commit()
        return ChatResponse(response="", intent="escalation", confidence=1.0)

    # 1. Initialize or retrieve session state
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "state": "idle",
            "lead_data": {"name": None, "budget": None, "contact": None}
        }

    session = SESSION_STORE[session_id]

    response_text = ""
    intent = ""
    confidence = 0.0

    # 2. Handle Lead Capture Logic
    if session["state"] == "collecting_lead":
        lead_data = session["lead_data"]

        # Find first missing field in sequence: name -> budget -> contact
        missing_field = None
        if lead_data["name"] is None:
            missing_field = "name"
        elif lead_data["budget"] is None:
            missing_field = "budget"
        elif lead_data["contact"] is None:
            missing_field = "contact"

        if missing_field:
            # Save current message to the missing field
            lead_data[missing_field] = user_msg

            # Check if all fields are now filled
            if all(lead_data.values()):
                # Persistence: Save to leads table
                try:
                    # Simple conversion for budget; if it fails, we store the string or 0.0
                    budget_val = float(user_msg) if missing_field == "budget" else lead_data["budget"]
                    if missing_field == "budget":
                        lead_data["budget"] = budget_val
                except (ValueError, TypeError):
                    # If budget conversion fails, we'll keep it as is or handle it.
                    # For this implementation, we'll try to save whatever we have.
                    pass

                new_lead = Lead(
                    name=lead_data["name"],
                    budget=lead_data["budget"] if isinstance(lead_data["budget"], (int, float)) else 0.0,
                    contact=lead_data["contact"],
                    agency_id=1 # Default agency
                )
                db.add(new_lead)
                db.commit()

                # Reset session
                session["state"] = "idle"
                session["lead_data"] = {"name": None, "budget": None, "contact": None}

                response_text = "Thank you! Your information has been saved. An agent will contact you shortly."
            else:
                # Prompt for the next missing field
                if lead_data["name"] and not lead_data["budget"]:
                    response_text = "Great, now please provide your budget:"
                elif lead_data["budget"] and not lead_data["contact"]:
                    response_text = "Lastly, what is your contact number?"

            intent = "lead_capture"
            confidence = 1.0
        else:
            # This case should technically not be reached if state is managed correctly
            session["state"] = "idle"
            response_text = "I'm sorry, there was an error. Let's start over."
            intent = "uncertain"
            confidence = 0.0

    # 3. Standard Logic (Idle State)
    else:
        prediction = predict_intent(user_msg)
        intent = prediction["intent"]
        confidence = prediction["confidence"]

        if intent in ["faq", "uncertain"]:
            response_text = get_rag_response(user_msg)
        elif intent == "lead_capture":
            session["state"] = "collecting_lead"
            response_text = "I can certainly help you with that! May I please have your full name first?"
        elif intent == "escalation":
            response_text = "Connecting you to a human agent... Please hold."

            # 1. Update all previous conversations for this session to 'escalated'
            db.query(Conversation).filter(Conversation.session_id == session_id).update({"status": "escalated"})

            # 2. Log the current user message as escalated
            user_conv = Conversation(session_id=session_id, role="user", message=user_msg, status="escalated")
            db.add(user_conv)

            # 3. Log the bot response as escalated
            bot_conv = Conversation(session_id=session_id, role="bot", message=response_text, status="escalated")
            db.add(bot_conv)

            db.commit()

            # 4. Immediate return to prevent fall-through to generic persistence block
            return ChatResponse(response=response_text, intent=intent, confidence=confidence)
        else:
            # Fallback for any other intents
            response_text = "I'm not sure how to help with that. Could you please rephrase or ask for an agent?"

    # 4. Persistence: Log conversation
    # User message
    user_conv = Conversation(session_id=session_id, role="user", message=user_msg)
    db.add(user_conv)

    # Bot response
    bot_conv = Conversation(session_id=session_id, role="bot", message=response_text)
    db.add(bot_conv)

    db.commit()

    return ChatResponse(response=response_text, intent=intent, confidence=confidence)

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve all messages for a session, sorted by time."""
    convs = db.query(Conversation).filter(Conversation.session_id == session_id).order_by(Conversation.created_at.asc()).all()
    return [{"role": c.role, "message": c.message, "status": c.status} for c in convs]
