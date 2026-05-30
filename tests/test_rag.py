import os
import sys
import time
from pathlib import Path

# Configure the project root in the Python search path
# This ensures backend.app.ml.rag can be resolved regardless of where the script is run
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from backend.app.ml.rag import get_rag_response
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

def run_test_queries():
    queries = [
        "What is the current price of a 5 marla plot in DHA Karachi?",
        "How does the token money process work in Bahria Town?",
        "What documents are needed for property transfer in Karachi?"
    ]

    print("\n" + "="*60)
    print("SupportIQ RAG Pipeline Inference Tests")
    print("="*60 + "\n")

    for i, query in enumerate(queries, 1):
        print(f"### Test Case {i}")
        print(f"Input User Query: {query}")

        # Handle free-tier rate limits by adding a short delay between calls
        time.sleep(4)

        start_time = time.perf_counter()
        try:
            response = get_rag_response(query)
            end_time = time.perf_counter()
            latency = end_time - start_time

            print(f"Latency: Generated in {latency:.2f}s")
            print(f"Gemini Generated Response:\n{response}")
        except Exception as e:
            print(f"Error: {str(e)}")

        print("-" * 40 + "\n")

if __name__ == "__main__":
    run_test_queries()
