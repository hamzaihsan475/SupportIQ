"""
Diagnostic script: load the trained intent classifier and run it against
a set of representative user messages. Bypasses the chat route entirely
so we can see exactly what the ML model predicts (intent label + raw
probability) and whether each prediction clears the 0.40 confidence
threshold used in backend/app/ml/classifier.py.

Each row also carries an EXPECTED intent so we can mark PASS / FAIL
against the model's top-class output.

Usage (from repo root):
    python backend/scripts/diagnose_intent.py
"""
import sys
import os

# Make the backend package importable when running this script directly.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import joblib
import numpy as np

from backend.app.ml.classifier import preprocess_text, MODEL_PATH  # noqa: E402

THRESHOLD = 0.40

# (message, expected_top_intent)
TEST_MESSAGES = [
    # --- Chitchat / casual (should classify as chitchat, top intent) ---
    ("kese ho?",                                                  "chitchat"),
    ("broo?",                                                     "chitchat"),
    ("wait??",                                                    "chitchat"),
    ("kya hal hai",                                               "chitchat"),
    ("ok",                                                        "chitchat"),
    ("thanks",                                                    "chitchat"),
    ("lol",                                                       "chitchat"),
    ("hmm",                                                       "chitchat"),
    ("habibi?",                                                   "chitchat"),
    # --- Real-estate out-of-scope (should classify as chitchat) ---
    ("you deal in property in hyderabad?",                       "chitchat"),
    # --- Escalation phrasing (should classify as escalation) ---
    ("i want to talk to admin",                                   "escalation"),
    ("I want to talk to a human",                                 "escalation"),
    # --- FAQ phrasing (should classify as faq) ---
    ("do you have listings in DHA",                               "faq"),
    # --- Numeric / currency (handled by lead_capture short-circuit in chatbot.py;
    #     classifier itself may route these however — we report what the model says) ---
    ("50000000",                                                  "lead_capture_or_other"),
    ("50 lakh",                                                   "lead_capture_or_other"),
]

def main() -> None:
    print(f"Model path: {MODEL_PATH}")
    print(f"Model exists: {os.path.exists(MODEL_PATH)}")
    if not os.path.exists(MODEL_PATH):
        print("ERROR: classifier.pkl not found — cannot run diagnosis.")
        return

    pipeline = joblib.load(MODEL_PATH)
    print(f"Model classes: {list(pipeline.classes_)}")
    print(f"Confidence threshold (from classifier.py): {THRESHOLD}")
    print()

    header = (
        f"{'message':<48} {'expected':<22} {'top_intent':<14} "
        f"{'conf':>6}  {'passes>=0.40':<14}  {'top3':<60}  {'verdict'}"
    )
    print(header)
    print("-" * len(header))

    pass_count = 0
    fail_count = 0
    for msg, expected in TEST_MESSAGES:
        processed = preprocess_text(msg)
        probs = pipeline.predict_proba([processed])[0]
        ranked = sorted(zip(pipeline.classes_, probs), key=lambda x: x[1], reverse=True)
        top_intent, top_conf = ranked[0]
        passes = "YES" if top_conf >= THRESHOLD else "no (=> uncertain)"
        top3 = ", ".join(f"{c}={p:.3f}" for c, p in ranked[:3])

        # Verdict: strict match when expected is a real intent label; permissive
        # (always PASS) when expected is "lead_capture_or_other" — those inputs
        # are routed by short-circuit logic in chatbot.py, not by the model.
        if expected == "lead_capture_or_other":
            verdict = "n/a (short-circuit)"
            pass_count += 1
        elif top_intent == expected:
            verdict = "PASS"
            pass_count += 1
        else:
            verdict = f"FAIL (got {top_intent})"
            fail_count += 1

        print(
            f"{msg!r:<48} {expected:<22} {top_intent:<14} "
            f"{top_conf:>6.3f}  {passes:<14}  {top3:<60}  {verdict}"
        )

    print()
    print(f"=== TOTALS: PASS={pass_count}  FAIL={fail_count}  n/a={len(TEST_MESSAGES)-pass_count-fail_count} ===")


if __name__ == "__main__":
    main()
