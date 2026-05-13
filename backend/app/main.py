from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from .database import engine, Base
from . import models
from .routes import predictor

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SupportIQ API")

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

@app.get("/api/listings")
async def get_listings():
    return [
        {"address": "DHA Phase 6, Karachi", "price": "Rs. 85,000,000", "bedrooms": 4, "bathrooms": 4, "area": 3600},
        {"address": "Gulshan-e-Iqbal, Karachi", "price": "Rs. 42,000,000", "bedrooms": 3, "bathrooms": 2, "area": 1800},
    ]

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request):
    return templates.TemplateResponse("listings.html", {"request": request})

@app.get("/predictor", response_class=HTMLResponse)
async def predictor_page(request: Request):
    return templates.TemplateResponse("predictor.html", {"request": request})