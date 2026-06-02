from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import pandas as pd

from .database import engine, Base
from . import models
from .routes import predictor, listings, chatbot

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SupportIQ API")

# Cache for location suggestions
LOCATIONS_CACHE = []

@app.on_event("startup")
async def load_locations():
    global LOCATIONS_CACHE
    try:
        # Path to Cleaned_Data.csv relative to this file
        # main.py is in backend/app/, csv is in backend/data/
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Cleaned_Data.csv')
        df = pd.read_csv(csv_path)
        if 'Address' in df.columns:
            LOCATIONS_CACHE = sorted(df['Address'].dropna().unique().tolist())
            print(f"Loaded {len(LOCATIONS_CACHE)} locations into cache.")
    except Exception as e:
        print(f"Error loading locations cache: {e}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(frontend_dir, "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictor.router)
app.include_router(listings.router)
app.include_router(chatbot.router, prefix="/api")

@app.get("/api/listings")
async def get_listings():
    return [
        {"address": "DHA Phase 6, Karachi", "price": "Rs. 85,000,000", "bedrooms": 4, "bathrooms": 4, "area": 3600},
        {"address": "Gulshan-e-Iqbal, Karachi", "price": "Rs. 42,000,000", "bedrooms": 3, "bathrooms": 2, "area": 1800},
    ]

@app.get("/api/locations")
async def get_locations():
    return LOCATIONS_CACHE

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request):
    return templates.TemplateResponse("listings.html", {"request": request})

@app.get("/predictor", response_class=HTMLResponse)
async def predictor_page(request: Request):
    return templates.TemplateResponse("predictor.html", {"request": request})