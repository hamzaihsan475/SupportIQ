"""
Diagnostic script: load the trained intent classifier and run it against
a small set of representative user messages. Bypasses the chat route
entirely so we can see exactly what the ML model predicts (intent label
+ raw probability) and whether each prediction clears the 0.40
confidence threshold used in backend/app/ml/classifier.py.

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

TEST_MESSAGES = [
    "you deal in property in hyderabad?",
    "i want to talk to admin",
    "I want to talk to a human",
    "can you help me",
    "hi",
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
    print(f"{'message':<45} {'processed':<45} {'top_intent':<14} {'conf':>6}  {'passes>=0.40':<14}  {'top3 (intent=conf)':<60}")
    print("-" * 180)

    for msg in TEST_MESSAGES:
        processed = preprocess_text(msg)
        probs = pipeline.predict_proba([processed])[0]
        # Sort class -> prob pairs by descending prob for the top-3 view.
        ranked = sorted(zip(pipeline.classes_, probs), key=lambda x: x[1], reverse=True)
        top_intent, top_conf = ranked[0]
        passes = "YES" if top_conf >= THRESHOLD else "no (=> uncertain)"
        top3 = ", ".join(f"{c}={p:.3f}" for c, p in ranked[:3])

        # Raw label if the threshold were NOT applied — this is what the model
        # actually thinks, separate from what classifier.py would return.
        print(f"{msg!r:<45} {processed!r:<45} {top_intent:<14} {top_conf:>6.3f}  {passes:<14}  {top3:<60}")


if __name__ == "__main__":
    main()
