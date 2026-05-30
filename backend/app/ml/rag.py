import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types

# 1. Load environment variables with proper fallback paths
env_path = os.path.join(os.path.dirname(__file__), '../../.env')
if not os.path.exists(env_path):
    env_path = '.env'

load_dotenv(dotenv_path=env_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Paths (Ensuring dynamic absolute path resolution)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "../../data/faiss_index.bin")
TEXTS_PATH = os.path.join(BASE_DIR, "../../data/faiss_texts.pkl")

# Knowledge Base: 40 Comprehensive Karachi Real Estate FAQs (2026 Market Data)
KNOWLEDGE_BASE = [
    "In DHA Phase 5 Karachi, a 1 kanal plot typically ranges from 8 to 12 Crore PKR, while 10 marla plots are between 4 to 6 Crore PKR, and 5 marla plots range from 2 to 3 Crore PKR.",
    "DHA Phase 6 plot rates in 2026 for 1 kanal are approximately 7 to 10 Crore PKR, 10 marla plots are 3 to 5 Crore PKR, and 5 marla plots are 1.5 to 2.5 Crore PKR.",
    "DHA Phase 7 property prices for 1 kanal plots are between 6 to 9 Crore PKR, 10 marla plots are 3 to 4.5 Crore PKR, and 5 marla plots range from 1.5 to 2 Crore PKR.",
    "DHA Phase 8 is a premium area where 1 kanal plots can go up to 15 Crore PKR, 10 marla plots range from 5 to 8 Crore PKR, and 5 marla plots are 2.5 to 4 Crore PKR.",
    "In Bahria Town Karachi Precinct 1, residential plots of 250 sq yards are typically valued between 80 Lakh to 1.2 Crore PKR.",
    "Bahria Town Karachi Precinct 12 plot prices for 250 sq yards usually fluctuate between 70 Lakh and 1.1 Crore PKR.",
    "Bahria Town Karachi Precinct 15 plots of 250 sq yards are generally priced between 65 Lakh and 95 Lakh PKR.",
    "Bahria Town Karachi Precinct 31 plots for 250 sq yards are typically valued between 60 Lakh and 90 Lakh PKR.",
    "The token money process for booking a plot starts with a booking application, followed by a payment of 100,000 to 500,000 PKR as a security deposit.",
    "After token payment, the society issues a confirmation letter; the buyer must then complete the full downpayment within 15 to 30 days to secure the plot.",
    "DHA Karachi transfer fees for a 1 kanal plot range from 2 to 5 Lakh PKR, whereas 10 marla costs 1 to 3 Lakh PKR and 5 marla costs 0.5 to 2 Lakh PKR.",
    "Bahria Town Karachi transfer fees consist of a plot-size based fee plus a processing charge, typically ranging from 50,000 to 200,000 PKR total.",
    "Essential documents for buying/selling in Karachi include a valid CNIC, the Original Allotment Letter, a signed Transfer Form, and a No Demand Certificate (NDC).",
    "The No Demand Certificate (NDC) is critical as it proves all society dues and taxes have been paid before a transfer is approved.",
    "A standard installment plan in Bahria Town Karachi involves a 10-20% downpayment followed by equal quarterly payments over a period of 3 to 5 years.",
    "Possession of a plot is typically granted after 80% of the total payment is cleared and the society has completed the necessary infrastructure development.",
    "In Clifton, 270 sq yard residential plots are high-value assets, often ranging from 15 to 30 Crore PKR depending on the block.",
    "Clifton luxury apartments in 2026 are priced between 4 Crore and 10 Crore PKR based on the floor, view, and total square footage.",
    "Gulshan-e-Iqbal residential plots of 120 sq yards typically range from 2 to 5 Crore PKR, depending on the proximity to main roads.",
    "Apartments in Gulshan-e-Iqbal are generally priced between 1.5 Crore and 4 Crore PKR for standard 3-bedroom units.",
    "North Nazimabad apartment prices vary by block, with premium units ranging from 2 Crore to 6 Crore PKR.",
    "Gulistan-e-Jauhar apartments are more affordable, typically ranging from 1 Crore to 3 Crore PKR depending on the society and amenities.",
    "To verify property ownership in DHA, you must visit the DHA office with the plot number and request a formal 'Verification Letter'.",
    "Bahria Town Karachi property verification is conducted at their head office by presenting the allotment letter and CNIC for current owner confirmation.",
    "SBCA (Sindh Building Control Authority) verification is essential to ensure that the building plans are approved and the construction is legal.",
    "Common real estate scams in Karachi include selling unverified 'files', fake allotment letters, and double-selling the same plot to multiple buyers.",
    "To avoid scams, always verify the NDC, check the society's online portal for the latest status, and ensure the seller is the actual owner.",
    "Capital Gains Tax (CGT) in Sindh is applied to property sales; the rate varies from 3% to 15% depending on how long the property was held.",
    "Standard stamp duty rates in Sindh for property registration are approximately 3% to 4% of the government-valued property price.",
    "A 'plot file' represents the right to a future plot that has not yet been physically allocated or numbered by the society.",
    "A 'plot' is a specific, physically identified piece of land with a unique plot number and a defined location on the society map.",
    "Buying a file is generally cheaper and riskier, while buying a plot is more expensive but provides immediate certainty of location.",
    "In DHA Phase 8, the most sought-after sectors currently offer the highest premiums due to rapid infrastructure development.",
    "DHA Phase 6 is preferred for its established residential community and proximity to the coast, keeping prices stable and high.",
    "Bahria Town Karachi's quarterly installment plans are popular among investors due to the flexibility of payment schedules.",
    "The transfer process in Bahria Town usually takes 7 to 14 working days once all documents are verified and fees are paid.",
    "Leasing a property in Clifton requires a valid title deed and verification from the Sindh government land records department.",
    "Commercial properties in Clifton offer an annual rental yield of approximately 5% to 8% depending on the tenant and location.",
    "Merging two adjacent plots in DHA requires an application to the DHA building control department and payment of a specific merge fee.",
    "Updating the name on a lease document in DHA involves submitting the current lease deed, an application, and the requisite transfer fees."
]

# 3. Initialize Embedding Model
model = SentenceTransformer('all-MiniLM-L6-v2')

def setup_index():
    """Sets up the FAISS index, ensuring directory exists, or creating it from the knowledge base."""
    if os.path.exists(INDEX_PATH) and os.path.exists(TEXTS_PATH):
        # Load existing index and texts
        index = faiss.read_index(INDEX_PATH)
        with open(TEXTS_PATH, 'rb') as f:
            texts = pickle.load(f)
        return index, texts
    else:
        # Ensure the data directory exists before saving
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

        # Generate embeddings for knowledge base
        embeddings = model.encode(KNOWLEDGE_BASE)
        embeddings = np.array(embeddings).astype('float32')

        # Build FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        # Save index and texts to disk
        faiss.write_index(index, INDEX_PATH)
        with open(TEXTS_PATH, 'wb') as f:
            pickle.dump(KNOWLEDGE_BASE, f)

        return index, KNOWLEDGE_BASE

# Load index and texts into memory
index, texts = setup_index()

# 4. Initialize Gemini Client
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

def get_rag_response(query: str) -> str:
    """
    Retrieves top 3 similar context pieces from the Karachi Real Estate KB
    and generates a response using Gemini 2.5 Flash with strict formatting and error routing.
    """
    try:
        # Step A: Embed the query
        query_embedding = model.encode([query]).astype('float32')

        # Step B: Search FAISS index for Top 3 matches
        D, I = index.search(query_embedding, k=3)

        # Step C: Retrieve the text pieces safely
        retrieved_context = [texts[i] for i in I[0] if i < len(texts)]
        context_text = "\n".join(f"- {ctx}" for ctx in retrieved_context)

        # Step D: Native System Prompt Configuration
        system_prompt = (
            "You are an expert Karachi Real Estate Assistant. "
            "Your goal is to provide accurate information about the Karachi real estate market based ONLY on the provided context. "
            "If the user's question cannot be answered using the provided context, politely inform them that you do not have that information in your database and decline to answer. "
            "Do not use external knowledge or make up facts. "
            "Keep your response concise and professional in markdown format."
        )

        # Step E: Format user query payload without mixing text contamination
        user_content = f"Context:\n{context_text}\n\nUser Question: {query}"

        # Step F: Generate Content via stable Gemini 2.5 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,  # 0.0 prevents hallucinations, strictly forces RAG context usage
            )
        )
        return response.text

    except Exception as e:
        # Gracefully handle API errors or 429 exceptions without crashing your FastAPI server
        return f"Error generating response: {str(e)}"
