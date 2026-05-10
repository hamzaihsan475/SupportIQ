import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import pickle
import os

def train_and_save_model():
    # Load the data
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct path to the CSV file (relative to script location)
    csv_path = os.path.join(script_dir, '..', '..', 'data', 'Cleaned_Data.csv')
    df = pd.read_csv(csv_path)

    # Drop Unnamed: 0 column if it exists
    if 'Unnamed: 0' in df.columns:
        df = df.drop('Unnamed: 0', axis=1)

    # Prepare features and target
    # Features: Address, NoOfBedrooms, NoOfBathrooms, AreaSqYards
    # Target: Price
    X = df[['Address', 'NoOfBedrooms', 'NoOfBathrooms', 'AreaSqYards']]
    y = df['Price']

    # Encode the Address column using Label Encoding
    le = LabelEncoder()
    X['Address_encoded'] = le.fit_transform(X['Address'])
    # Drop the original Address column
    X = X.drop('Address', axis=1)

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train Linear Regression
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_r2 = r2_score(y_test, lr_pred)
    print(f"Linear Regression R² Score: {lr_r2}")

    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_r2 = r2_score(y_test, rf_pred)
    print(f"Random Forest R² Score: {rf_r2}")

    # Choose the better model based on R² score
    if rf_r2 > lr_r2:
        best_model = rf
        print("Random Forest performed better.")
    else:
        best_model = lr
        print("Linear Regression performed better.")

    # Ensure the models directory exists
    model_dir = os.path.join(script_dir, '..', '..', 'models')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # Save the best model
    model_path = os.path.join(model_dir, 'price_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)

    # Save the label encoder
    encoder_path = os.path.join(model_dir, 'label_encoder.pkl')
    with open(encoder_path, 'wb') as f:
        pickle.dump(le, f)

    print("Model and label encoder saved successfully.")

def predict_price(address, bedrooms, bathrooms, area):
    """
    Predict the price of a property based on its features.

    Args:
        address (str): The address of the property
        bedrooms (int/float): Number of bedrooms
        bathrooms (int/float): Number of bathrooms
        area (int/float): Area in square yards

    Returns:
        float: Predicted price
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Load the model and label encoder
    model_path = os.path.join(script_dir, '..', '..', 'models', 'price_model.pkl')
    encoder_path = os.path.join(script_dir, '..', '..', 'models', 'label_encoder.pkl')

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    with open(encoder_path, 'rb') as f:
        le = pickle.load(f)

    # Prepare the input data
    # Encode the address
    try:
        address_encoded = le.transform([address])[0]
    except ValueError:
        # If the address is not in the label encoder's classes, we might need to handle it
        # For simplicity, we'll assign a default value or raise an error
        raise ValueError(f"Address '{address}' not found in training data")

    # Create feature array
    X_input = np.array([[address_encoded, bedrooms, bathrooms, area]])

    # Make prediction
    predicted_price = model.predict(X_input)[0]

    return predicted_price

if __name__ == "__main__":
    train_and_save_model()