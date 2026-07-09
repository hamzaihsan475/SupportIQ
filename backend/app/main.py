import os
# --- Framework Safety Flags (Bypasses TensorFlow/Protobuf Version Conflicts) ---
os.environ["STORAGE_OPTIONS"] = ""
os.environ["FORCE_TF_AVAILABLE"] = "0"
os.environ["AA_IMPORT_TENSORFLOW"] = "0"
os.environ["USE_TORCH"] = "1"  # Forces Transformers to run cleanly on PyTorch

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd

from .auth import verify_admin_credentials
from .database import engine, Base
from . import models
from .routes import predictor, listings, chatbot, admin

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SupportIQ API")

# Cache for location suggestions
LOCATIONS_CACHE = []

@app.on_event("startup")
async def load_locations():
    global LOCATIONS_CACHE
    try:
        # Path to Cleaned_Data.csv relative to this file
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Cleaned_Data.csv')
        df = pd.read_csv(csv_path)
        if 'Address' in df.columns:
            LOCATIONS_CACHE = sorted(df['Address'].dropna().unique().tolist())
            print(f"Loaded {len(LOCATIONS_CACHE)} locations into cache.")
    except Exception as e:
        print(f"Error loading locations cache: {e}")

# Base Directories and Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(BASE_DIR, "frontend")

# Standard CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Jinja2 Templates
app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(frontend_dir, "templates"))

# --- APIRouters Inclusion ---
app.include_router(chatbot.router, prefix="/api")
app.include_router(predictor.router)
app.include_router(listings.router)
app.include_router(admin.router, prefix="/api/admin")

# --- Core API Endpoints ---
@app.get("/api/listings")
async def get_listings():
    return [
        {"address": "DHA Phase 6, Karachi", "price": "Rs. 85,000,000", "bedrooms": 4, "bathrooms": 4, "area": 3600},
        {"address": "Gulshan-e-Iqbal, Karachi", "price": "Rs. 42,000,000", "bedrooms": 3, "bathrooms": 2, "area": 1800},
    ]

@app.get("/api/locations")
async def get_locations():
    return LOCATIONS_CACHE

# --- HTML Frontend Page Web Routes ---
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request):
    return templates.TemplateResponse("listings.html", {"request": request})

@app.get("/listings/view/{listing_id}", response_class=HTMLResponse)
async def listing_detail_page(request: Request, listing_id: int):
    """Server-renders the detail-page shell. The template's JS fetches the
    full listing data (including submitter fields) from GET /listings/{id}
    and renders it client-side. Listing-id is passed in so the template can
    render the right data even before JS hydrates.
    """
    return templates.TemplateResponse(
        "listing_detail.html",
        {"request": request, "listing_id": listing_id},
    )

@app.get("/predictor", response_class=HTMLResponse)
async def predictor_page(request: Request):
    return templates.TemplateResponse("predictor.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, _=Depends(verify_admin_credentials)):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/submit-listing", response_class=HTMLResponse)
async def submit_listing_page(request: Request):
    return templates.TemplateResponse("submit_listing.html", {"request": request})