from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any

from ..database import get_db
from ..models import Lead, Conversation
from ..ml.classifier import predict_intent
from ..ml.rag import get_rag_response

router = APIRouter()

# In-memory session store to manage chatbot states
# Structure: { session_id: {"state": str, "lead_data": dict} }
SESSION_STORE: Dict[str, Any] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    session_id = request.session_id
    user_message = request.message

    # 1. Initialize or fetch session state
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "state": "idle",
            "lead_data": {"name": None, "budget": None, "contact": None}
        }

    session = SESSION_STORE[session_id]
    state = session["state"]
    lead_data = session["lead_data"]

    response_text = ""
    intent = ""
    confidence = 0.0

    # 2. Logic Flow
    if state == "collecting_lead":
        # Determine which field to collect next
        if lead_data["name"] is None:
            field = "name"
            prompt = "Great! Lastly, what is your contact number?" # Wait, order is name -> budget -> contact
        elif lead_data["budget"] is None:
            field = "budget"
        elif lead_data["contact"] is None:
            field = "contact"
        else:
            field = None

        # If we are here, we are collecting the missing field
        if field:
            # Save current message to the missing field
            # The prompt says name -> budget -> contact
            # Let's determine the target field based on what's missing
            target_field = None
            if lead_data["name"] is None:
                target_field = "name"
            elif lead_data["budget"] is None:
                target_field = "budget"
            elif lead_data["contact"] is None:
                target_field = "contact"

            lead_data[target_field] = user_message

            # Check if all fields are now collected
            if all(lead_data.values()):
                # Save to database
                new_lead = Lead(
                    name=lead_data["name"],
                    budget=float(lead_data["budget"]) if lead_data["budget"] and lead_data["budget"].replace('.','',1).isdigit() else 0.0,
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
                # Prompt for the next missing piece
                if lead_data["name"] is not None and lead_data["budget"] is None:
                    response_text = "Great, now please provide your budget"
                elif lead_data["budget"] is not None and lead_data["contact"] is None:
                    response_text = "Lastly, what is your contact number?"
                else:
                    # This case shouldn't happen based on flow but for safety:
                    response_text = "Could you please provide more details?"

            intent = "lead_capture"
            confidence = 1.0
        else:
            # This shouldn't be reachable if state is collecting_lead and target_field is None
            state = "idle" # Fallback

    else: # Standard flow (state == "idle")
        prediction = predict_intent(user_message)
        intent = prediction["intent"]
        confidence = prediction["confidence"]

        if intent in ["faq", "uncertain"]:
            response_text = get_rag_response(user_message)
        elif intent == "lead_capture":
            session["state"] = "collecting_lead"
            response_text = "I can certainly help you with that! May I please have your full name first?"
        elif intent == "escalation":
            response_text = "Connecting you to a human agent... Please hold."
        else:
            response_text = "I'm not sure how to help with that. Could you please rephrase your question?"

    # 3. Persistence: Save conversation history
    # User message
    user_conv = Conversation(session_id=session_id, role="user", message=user_message)
    db.add(user_conv)
    # Bot response
    bot_conv = Conversation(session_id=session_id, role="bot", message=response_text)
    db.add(bot_conv)
    db.commit()

    return ChatResponse(response=response_text, intent=intent, confidence=confidence)
