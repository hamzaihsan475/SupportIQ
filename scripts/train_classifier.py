import pandas as pd
import numpy as np
import re
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    phone_pattern = r'(\+?92|0)?\s*3\d{2}[-\s]?\d{3}[-\s]?\d{4}'
    text = re.sub(phone_pattern, '__PHONE__', text)
    text = re.sub(r'\s+', ' ', text)
    return text

# Load dataset
df = pd.read_csv('backend/data/intent_dataset.csv')
df['text'] = df['text'].apply(preprocess_text)
X = df['text']
y = df['intent']

# Stratified Split (80/20)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Build Pipeline
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_df=0.95, min_df=2)),
    ('clf', CalibratedClassifierCV(estimator=LinearSVC(C=1.0, random_state=42, dual=False), method='sigmoid'))
])

pipeline.fit(X_train, y_train)

# Export model
model_dir = 'backend/models'
if not os.path.exists(model_dir):
    os.makedirs(model_dir)
joblib.dump(pipeline, os.path.join(model_dir, 'classifier.pkl'))
print(f"Model successfully trained and saved to {model_dir}/classifier.pkl")
