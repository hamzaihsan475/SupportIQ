"""
Reports held-out (80/20 stratified) accuracy for the new 4-class model by
reproducing the exact training split from scripts/train_classifier.py
(random_state=42, stratify=intent).
"""
import os
import sys
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.ml.classifier import preprocess_text  # noqa: E402

def main() -> None:
    df = pd.read_csv('backend/data/intent_dataset.csv')
    df['text'] = df['text'].apply(preprocess_text)
    X = df['text']
    y = df['intent']

    print(f"Total dataset rows: {len(df)}")
    print(f"Class balance:")
    print(y.value_counts().to_string())
    print()

    # Reproduce exact training split from scripts/train_classifier.py
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_df=0.95, min_df=2)),
        ('clf', CalibratedClassifierCV(estimator=LinearSVC(C=1.0, random_state=42, dual=False), method='sigmoid'))
    ])
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"=== HELD-OUT ACCURACY (80/20 stratified split, random_state=42) ===")
    print(f"Test set size: {len(y_test)}")
    print(f"Overall accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print()
    print("=== PER-CLASS PRECISION / RECALL / F1 ===")
    print(classification_report(y_test, y_pred, digits=3))

    # Persist accuracy + class list for the report
    print(f"Classes seen by the new model: {list(pipeline.classes_)}")

if __name__ == "__main__":
    main()
