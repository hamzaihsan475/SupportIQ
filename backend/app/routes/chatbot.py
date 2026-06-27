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

# ---------------------------------------------------------------------------
# Pre-classifier casual-chitchat guard
# ---------------------------------------------------------------------------
# The trained intent classifier (backend/models/classifier.pkl) was fit on
# 2,100 long templated real-estate sentences and has ZERO examples of
# greetings, small talk, or Roman Urdu. As a result, casual inputs like
# "broo?", "lol", "hmm", "wait??", "kese ho?" get confidently WRONG
# predictions (e.g. lead_capture @ 0.87, escalation @ 0.61), and the 0.40
# confidence threshold does NOT catch them because the wrong class still
# scores high. This guard short-circuits such inputs to a friendly Gemini
# response BEFORE predict_intent() runs.
#
# Keyword list sourced from token-frequency analysis of the actual
# 2,100-row training set (backend/data/intent_dataset.csv) and the FAQ
# knowledge base already used in backend/app/ml/rag.py — every word here
# appears at least once in one of those two sources.
RE_ESTATE_KEYWORDS: set[str] = {
    # Locations (from intent_dataset.csv top-frequency + rag.py KNOWLEDGE_BASE)
    "dha", "bahria", "gulberg", "johar", "clifton", "gulshan", "emaar",
    "giga", "mall", "blue", "area", "phase", "sector",
    # Property / unit terms
    "plot", "house", "apartment", "flat", "villa", "shop", "file",
    "marla", "kanal", "bhk", "penthouse", "studio", "commercial",
    "residential", "property", "properties", "listing", "listings",
    # Action / intent terms
    "buy", "sell", "rent", "lease", "invest", "booking", "book",
    "available", "sale", "buying", "selling",
    # Money / pricing
    "price", "prices", "pricing", "budget", "rate", "rates", "lakh",
    "lakhs", "crore", "crores", "pkr", "rs", "rupee", "rupees",
    "installment", "downpayment", "token", "money", "fee", "fees",
    "transfer", "registry", "possession", "charges", "tax", "cgt",
    "stamp", "duty",
    # People / process
    "agent", "admin", "human", "owner", "broker", "contact",
    "escalate", "escalation", "complaint", "manager",
}

# Word-count cutoff for the chitchat guard. <=3 chosen because the 2,100-row
# training set has ZERO examples with <=3 words (verified by direct scan of
# intent_dataset.csv — the shortest message is 6 words), so this cutoff
# cannot swallow a legitimate classifier input. Every confirmed-broken
# casual input ("broo?", "lol", "hmm", "wait??", "kese ho?", "hi", "ok",
# "thanks") is 1 word; every must-NOT-be-rerouted input from the test set
# is >=6 words.
WORD_COUNT_CUTOFF: int = 3


# Lead-field filler-word list. Vocabulary sourced directly from the words
# already enumerated in is_casual_chitchat()'s docstring and the pre-classifier
# guard's design comment above (the same "wait / hi / hello / ok / okay / ya /
# yeah / hmm / lol / thanks / bye / bro / kese" set the prior session used to
# define casual chitchat). We reuse that vocabulary here rather than building
# a brand-new list, because the same class of inputs (single-word greetings
# and fillers typed mid-funnel) is exactly what gets silently mis-accepted as
# a name, budget, or contact.
#
# Roman Urdu additions: a live test surfaced "ruko" (Urdu for "wait") being
# silently accepted as a contact value, because the prior list was English-
# only and the contact field had no validation. The Roman Urdu bare single-
# word fillers below were sourced from the chitchat class in
# backend/data/intent_dataset.csv (already reviewed and approved as
# authentic Karachi-style chitchat) plus the canonical words the task
# description explicitly named. Multi-word fillers ("salam bhai", "acha
# theek hai", "ok done bhai") are filtered out by the single-token check
# in _is_single_filler_word() below — only bare single words need to be in
# this set.
LEAD_FILLER_WORDS: set[str] = {
    # English fillers / acknowledgements / greetings
    "wait", "hi", "hello", "hey", "ok", "okay", "okk", "ya", "yeah",
    "yep", "yup", "yess", "hmm", "hm", "lol", "lmao", "haha", "thanks",
    "thank", "thx", "ty", "thnx", "thanx", "bye", "bro", "bruh",
    "w8", "huh", "eh", "hehe", "ha", "wow", "omg", "nice", "cool",
    "great", "good", "awesome", "amazing", "perfect", "alright", "sure",
    "no", "nope", "nah", "yes", "morning", "afternoon", "evening",
    "night", "gm", "gn", "kese", "kaise", "kaisy", "kaisay",
    # Roman Urdu bare fillers / greetings / acknowledgements (single-word only;
    # multi-word variants like "salam bhai" / "haan yaar" fall through as
    # they are not single-token after the \b\w+\b split).
    "ruko", "acha", "theek", "thik", "thk", "haan", "han", "nahi",
    "nahin", "nhi", "ni", "sahi", "shukriya", "shukria", "salam",
    "salaam", "aoa", "adaab", "walaikum", "meherbani", "mehrbani",
    "jazak", "jazakallah", "khuda", "phir", "chal", "subah", "bakhair",
    "bas", "kuch", "sab", "sb", "mast", "mst", "alhamdulillah",
    "alhamdullilah", "fi", "kyun", "kyu", "kya", "yaar", "bhai",
    "baji", "bajiya",
}


def _is_single_filler_word(message: str) -> bool:
    """
    Returns True if `message` is exactly one word AND that word is in
    LEAD_FILLER_WORDS (after stripping punctuation/whitespace and
    lowercasing). Multi-word inputs and anything not in the set return False.
    Used only inside the collecting_lead branch to reject filler words typed
    in response to a name, budget, or contact prompt.
    """
    if not isinstance(message, str):
        return False
    # \b\w+\b strips surrounding punctuation/quotes so "wait??" and "hi."
    # still match their base words.
    words = re.findall(r"\b\w+\b", message.lower().strip())
    if len(words) != 1:
        return False
    return words[0] in LEAD_FILLER_WORDS


def is_casual_chitchat(message: str) -> bool:
    """
    Pre-classifier guard. Returns True for inputs that are clearly casual
    small-talk (greetings, Roman Urdu, filler like "broo?/lol/hmm/ok/hi/
    thanks") rather than a real-estate question.

    Rule: word_count <= WORD_COUNT_CUTOFF AND no real-estate keyword
    appears in the (lowercased) message.

    Only safe to call in the idle/default chat path. The collecting_lead
    branch has its own short-circuit logic (numeric/currency/contact +
    HATCH 1 / HATCH 2) and is intentionally NOT routed through this guard.
    """
    if not isinstance(message, str):
        return False
    msg_lower = message.lower()
    words = re.findall(r"\b\w+\b", msg_lower)
    if len(words) > WORD_COUNT_CUTOFF:
        return False
    if not words:  # empty / punctuation-only — treat as chitchat
        return True
    return not any(kw in msg_lower for kw in RE_ESTATE_KEYWORDS)


def _chitchat_via_gemini(user_msg: str) -> str:
    """
    Direct Gemini call for casual chitchat. Reuses the module-level Gemini
    client from backend.app.ml.rag (same singleton — no second client).
    Deliberately does NOT invoke the FAISS / RAG pipeline, because these
    messages are unrelated to the property FAQ knowledge base.
    """
    # Lazy import to avoid forcing backend.app.ml.rag initialization
    # (which loads the embedding model and FAISS index) on every chitchat
    # call when it's already loaded once at startup.
    from backend.app.ml.rag import client, types

    try:
        system_prompt = (
            "You are SupportIQ, a friendly Karachi real-estate assistant. "
            "The user just sent a casual / non-real-estate message. "
            "Reply briefly (1-2 sentences), warmly, and gently steer the "
            "conversation back to how you can help with property questions "
            "in Karachi (buying, selling, renting, listings, prices, DHA, "
            "Bahria Town, Clifton, Gulshan-e-Iqbal, etc.). Do not pretend "
            "to know about non-property topics — keep redirecting to real "
            "estate."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,  # warmer than the FAQ path (0.0) for chitchat
            ),
        )
        return response.text
    except Exception:
        # Mirror get_rag_response()'s error-fallback style so a Gemini
        # outage does not take down the chat route.
        return (
            "Hey there! I'm here to help with Karachi real-estate questions "
            "(buy/sell/rent, DHA, Bahria Town, prices, etc.). What are you looking for?"
        )

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
            # LEAD-FIELD FILLER VALIDATION (name + budget + contact).
            # The classifier is comfortable mis-routing single-word greetings
            # as lead_capture, and the numeric/currency/contact short-circuit
            # above only catches inputs that look like the *next* field —
            # it does nothing for bare filler words typed into the name,
            # budget, or contact slot. Without this check, "wait" silently
            # becomes the user's name, "hi" silently becomes their budget,
            # and Roman Urdu fillers like "ruko" silently become the contact
            # value. We reject only single-word filler matches against
            # LEAD_FILLER_WORDS (the same vocabulary already enumerated by
            # the pre-classifier is_casual_chitchat() guard above, plus the
            # Roman Urdu fillers sourced from the intent_dataset.csv chitchat
            # class) — multi-word inputs, real names, real numeric/currency
            # budgets, and contact-shaped input (phones / emails) all pass
            # through unchanged. Phones/emails are inherently multi-token
            # under the \b\w+\b split used by _is_single_filler_word, so
            # there is no overlap with the existing contact-shape
            # short-circuit above.
            if missing_field in ("name", "budget", "contact") and _is_single_filler_word(user_msg):
                if missing_field == "name":
                    response_text = (
                        "Sorry, I didn't quite catch that — could you tell "
                        "me your full name?"
                    )
                elif missing_field == "budget":
                    response_text = (
                        "Sorry, could you share your budget so I can help "
                        "find the right options?"
                    )
                else:  # missing_field == "contact"
                    response_text = (
                        "Sorry, could you share a valid contact number or "
                        "email so an agent can reach you?"
                    )

                # Mirror ESCAPE HATCH 2's persistence pattern: log both
                # turns so the admin conversation log reflects what the
                # user typed, but do NOT change session state, do NOT
                # advance the missing field, and do NOT save to lead_data.
                user_conv = Conversation(session_id=session_id, role="user", message=user_msg)
                db.add(user_conv)
                bot_conv = Conversation(session_id=session_id, role="bot", message=response_text)
                db.add(bot_conv)
                db.commit()

                return ChatResponse(
                    response=response_text,
                    intent="lead_capture",
                    confidence=1.0,
                )

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
        # PRE-CLASSIFIER GUARD: catch casual chitchat (greetings, Roman
        # Urdu, filler like "broo?"/"lol"/"hmm"/"wait??"/"kese ho?") that
        # the trained classifier confidently misroutes as lead_capture /
        # escalation. We only apply this in the idle state — mid-lead-
        # capture has its own short-circuit logic (HATCH 1 / HATCH 2 +
        # numeric/currency/contact) above that we must not interfere with.
        if is_casual_chitchat(user_msg):
            response_text = _chitchat_via_gemini(user_msg)
            intent = "chitchat"
            confidence = 1.0
        else:
            prediction = predict_intent(user_msg)
            intent = prediction["intent"]
            confidence = prediction["confidence"]

            if intent in ["faq", "uncertain"]:
                response_text = get_rag_response(user_msg)
            elif intent == "chitchat":
                # Safety-net for casual / non-real-estate messages that slipped
                # past the pre-classifier is_casual_chitchat() guard (e.g.
                # longer casual messages that exceed the WORD_COUNT_CUTOFF).
                # Same routing as the guard: friendly Gemini response, no
                # escalation, no lead capture, no RAG, no session-state change.
                response_text = _chitchat_via_gemini(user_msg)
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
