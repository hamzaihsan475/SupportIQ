# SupportIQ — AI-Powered Real Estate Platform


## About
SupportIQ is a full-stack web application for Pakistani real estate agencies.
It combines property listing management, AI-based price prediction,
and an NLP-powered support chatbot into a single platform.

## Tech Stack
- **Backend:** Python, FastAPI, SQLite
- **Frontend:** React.js
- **ML:** scikit-learn, FAISS, Google Gemini API


## Setup Instructions

### Dataset
Download `Cleaned_Data.csv` and place it in `backend/data/` folder manually.
Dataset is not included in the repository.

### Models
After placing the dataset, run the following command to train the model:
```bash
python -m backend.app.ml.price_model
```
This will generate `price_model.pkl` and `label_encoder.pkl` in `backend/models/`.