from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from pydantic import BaseModel
import re

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

        # ESCAPE HATCH: Before assigning the incoming message to the next missing
        # lead field, re-classify the message so a user who actually wants to
        # escalate or ask an FAQ mid-flow is not trapped in the lead funnel.
        # This uses the same predict_intent() + 0.40 threshold as the idle path.

        # NUMERIC / CURRENCY / CONTACT SHORT-CIRCUIT: the trained classifier
        # was never taught what a bare numeric budget (e.g. "50000000") looks
        # like, so it mis-labels pure digit strings as "escalation" with high
        # confidence. Same story for budget-shaped phrases that contain
        # "lakh" / "crore" / "pkr" — those happen to land in the lead_capture
        # class today but only by accident, and any future retraining could
        # break them. Same for contact-shaped strings (phone / email) when
        # we're on the contact step. Skip the classifier entirely for inputs
        # that clearly match the field we're currently asking for, and let
        # them fall through to the field-assignment block below.
        skip_classification = False
        if missing_field == "budget":
            msg_lower = user_msg.lower().strip()
            # Pure number: digits with optional commas/spaces/periods.
            # Examples: "50000000", "50,000,000", "5000000.50", "50 000 000"
            is_pure_number = bool(re.fullmatch(r"[\d][\d,\s\.]*", msg_lower)) and any(ch.isdigit() for ch in msg_lower)
            # Currency keywords common in Pakistani real-estate conversation.
            currency_tokens = ("lakh", "lac", "lacs", "crore", "crores", "pkr", "rs.", "rs ", "rupees", "rupee")
            has_currency_token = any(tok in msg_lower for tok in currency_tokens)
            if is_pure_number or has_currency_token:
                skip_classification = True
        elif missing_field == "contact":
            msg_compact = user_msg.strip()
            # Phone-shaped: mostly digits with optional +, -, spaces.
            # Examples: "03001234567", "+92 300 1234567", "0300-1234567"
            is_phone_like = bool(re.fullmatch(r"[\+]?[\d][\d\-\s]{6,}", msg_compact)) and sum(ch.isdigit() for ch in msg_compact) >= 7
            # Email-shaped: contains "@".
            is_email_like = "@" in msg_compact
            if is_phone_like or is_email_like:
                skip_classification = True

        mid_flow_prediction = predict_intent(user_msg) if not skip_classification else {"intent": "lead_capture", "confidence": 1.0}
        mid_flow_intent = mid_flow_prediction["intent"]
        mid_flow_confidence = mid_flow_prediction["confidence"]

        # ESCAPE HATCH 1: Mid-flow escalation request — exit lead capture, save
        # whatever partial lead data we already have, then run the standard
        # escalation path below.
        # Guard parity with HATCH 2 below: only fire when there is a real lead
        # field currently being collected (missing_field is not None). The
        # numeric/currency/contact short-circuit above means this hatch only
        # ever sees messages that the classifier genuinely thinks are
        # escalation, and only when we are legitimately mid-funnel.
        if mid_flow_intent == "escalation" and mid_flow_confidence >= 0.40 and missing_field is not None:
            # Persist partial lead if any field was already collected.
            # All Lead fields are nullable, so None values are allowed.
            if any(v is not None for v in lead_data.values()):
                try:
                    # Coerce budget to float if user already gave one.
                    partial_budget = lead_data["budget"]
                    if isinstance(partial_budget, str):
                        try:
                            partial_budget = float(partial_budget)
                        except (ValueError, TypeError):
                            partial_budget = None
                    partial_lead = Lead(
                        name=lead_data["name"],
                        budget=partial_budget,
                        contact=lead_data["contact"],
                        agency_id=1  # Default agency
                    )
                    db.add(partial_lead)
                    db.commit()
                except Exception:
                    # Never block an escalation because of a partial-write failure.
                    db.rollback()

            # Reset session back to the idle/default state, matching the
            # convention used elsewhere in this file.
            session["state"] = "idle"
            session["lead_data"] = {"name": None, "budget": None, "contact": None}

            # Fall through to the standard escalation path (intent/escalation
            # branch in the idle block) by jumping past the field-assignment
            # logic below. We do this by reusing the same response-building
            # and DB-escalation logic that idle-state escalation uses.
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

            return ChatResponse(response=response_text, intent=mid_flow_intent, confidence=mid_flow_confidence)

        # ESCAPE HATCH 2: Mid-flow FAQ — answer the user's question for this
        # turn and re-prompt for the SAME field they were on. We deliberately
        # do not invoke the full RAG pipeline mid-flow (the existing file style
        # is procedural and minimal); a brief acknowledgment + same-field
        # re-prompt keeps the funnel state consistent without the complexity
        # of re-entering RAG and then re-resuming lead capture.
        if mid_flow_intent == "faq" and mid_flow_confidence >= 0.40 and missing_field is not None:
            if missing_field == "name":
                response_text = "Happy to help with that — but first, may I please have your full name?"
            elif missing_field == "budget":
                response_text = "Good question — could you tell me your budget so I can match you with the right options?"
            elif missing_field == "contact":
                response_text = "Quick one before I wrap up: what is your contact number?"

            # Persist this turn's exchange but DO NOT change session state or
            # advance the missing field. The lead funnel continues from the
            # same step on the next message.
            user_conv = Conversation(session_id=session_id, role="user", message=user_msg)
            db.add(user_conv)
            bot_conv = Conversation(session_id=session_id, role="bot", message=response_text)
            db.add(bot_conv)
            db.commit()

            return ChatResponse(
                response=response_text,
                intent=mid_flow_intent,
                confidence=mid_flow_confidence,
            )

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
