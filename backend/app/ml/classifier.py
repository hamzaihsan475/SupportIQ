import re
import joblib
import os
import numpy as np

# Path to the saved model
MODEL_PATH = 'backend/models/classifier.pkl'

# Load model on module load
if os.path.exists(MODEL_PATH):
    pipeline = joblib.load(MODEL_PATH)
else:
    pipeline = None

def preprocess_text(text: str) -> str:
    """
    Normalizes text for intent classification:
    - Lowercase and strip whitespace
    - Normalizes Pakistani phone numbers to '__PHONE__'
    - Removes extra internal whitespace
    """
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Normalize phone numbers: +92, 03xx etc
    # Matches optional +92 or 0, followed by 3, then 9 more digits, allowing spaces/hyphens
    phone_pattern = r'(\+?92|0)?\s*3\d{2}[-\s]?\d{3}[-\s]?\d{4}'
    text = re.sub(phone_pattern, '__PHONE__', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text

def predict_intent(text: str) -> dict:
    """
    Predicts the intent of the given text using the loaded ML pipeline.
    If the confidence is below 0.40, the intent is marked as 'uncertain'.

    Args:
        text (str): The input query text.

    Returns:
        dict: A dictionary containing 'intent' and 'confidence'.
    """
    if pipeline is None:
        return {"intent": "uncertain", "confidence": 0.0}

    # 1. Preprocess input
    processed_text = preprocess_text(text)

    # 2. Get probability distributions
    # pipeline.predict_proba returns an array of probabilities for each class
    probabilities = pipeline.predict_proba([processed_text])[0]

    # 3. Extract highest probability and corresponding class
    max_idx = np.argmax(probabilities)
    confidence = probabilities[max_idx]
    intent = pipeline.classes_[max_idx]

    # 4. Apply confidence threshold
    if confidence < 0.40:
        intent = "uncertain"

    return {
        "intent": intent,
        "confidence": float(confidence)
    }
