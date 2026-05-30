# SupportIQ — AI-Powered Real Estate Platform

## Overview
SupportIQ is a comprehensive full-stack web application engineered for real estate agencies within the Pakistani market. The platform integrates property listing management, deterministic price prediction, and an advanced Natural Language Processing (NLP) support framework into a unified professional ecosystem.

## Tech Stack
- **Backend:** Python, FastAPI, SQLite
- **Frontend:** Jinja2 Templates, HTML5, CSS3, JavaScript (Vanilla)
- **Machine Learning:** scikit-learn, FAISS, Google Gemini API

## Core Features
- **Price Predictor:** A robust engine utilizing linear rule-based scaling and dynamic location validation to provide accurate market estimations.
- **Listings CRUD:** A dedicated real estate database management system designed for tenant agencies to maintain property portfolios.
- **Intent Classifier:** An SVM-driven query router that categorizes user interactions into FAQ, Lead Capture, or Escalation.
- **RAG Chatbot:** A semantic knowledge retrieval system leveraging FAISS for vector storage, integrated with Google Gemini API grounding for high-fidelity responses.

## Setup and Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd SupportIQ
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
```

### Step 3: Activate Virtual Environment
**Windows:**
```bash
.venv\Scripts\activate
```
**Mac/Linux:**
```bash
source .venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 5: Data Placement
Place the dataset `Cleaned_Data.csv` inside the `backend/data/` directory.

### Step 6: Environment Configuration
Create a file at `backend/.env` and insert the following configuration:
```env
GEMINI_API_KEY=your_key_here
```

### Step 7: Model Execution
**Train Price Predictor:**
```bash
python -m backend.app.ml.price_model
```
**Train Intent Classifier:**
Execute the `notebooks/classifier_training.ipynb` notebook.

### Step 8: Launch Application
```bash
uvicorn backend.app.main:app --reload
```
