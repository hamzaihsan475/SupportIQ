import sys
import os

# Ensure the project root is in the Python path
# This allows importing from backend.app.ml.classifier
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.ml.classifier import predict_intent

def run_verification():
    test_queries = [
        "bhai mujhe koi agent chahiye urgent",
        "5 marla plot ka kya rate hai bahria town mein",
        "I want to schedule a visit this weekend"
    ]

    print("\n" + "="*60)
    print(f"{'LIVE CLASSIFIER VERIFICATION':^60}")
    print("="*60 + "\n")

    for query in test_queries:
        result = predict_intent(query)
        intent = result['intent'].upper()
        confidence = result['confidence'] * 100

        print(f"Input Query: {query}")
        print(f"Predicted Intent: {intent}")
        print(f"Confidence Score: {confidence:.1f}%")
        print("-" * 30)

    print("\n" + "="*60)

if __name__ == "__main__":
    run_verification()
