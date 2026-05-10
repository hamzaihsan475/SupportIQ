import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
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

    # Apply log transformation to target
    y_log = np.log1p(y)

    # One-hot encode the Address column
    X = pd.get_dummies(X, columns=['Address'], prefix='Address', drop_first=False)

    # Split the data
    X_train, X_test, y_train_log, y_test_log = train_test_split(X, y_log, test_size=0.2, random_state=42)

    # Store the column order for later use in prediction
    training_columns = X_train.columns.tolist()

    # Train Linear Regression
    lr = LinearRegression()
    lr.fit(X_train, y_train_log)
    lr_pred_test_log = lr.predict(X_test)
    lr_pred_train_log = lr.predict(X_train)
    # Convert predictions back to original scale
    lr_pred_test = np.expm1(lr_pred_test_log)
    lr_pred_train = np.expm1(lr_pred_train_log)
    # Convert y_train_log and y_test_log back to original scale for metrics
    y_train = np.expm1(y_train_log)
    y_test = np.expm1(y_test_log)
    # Metrics for Linear Regression
    lr_r2_test = r2_score(y_test, lr_pred_test)
    lr_r2_train = r2_score(y_train, lr_pred_train)
    lr_rmse_test = np.sqrt(mean_squared_error(y_test, lr_pred_test))
    lr_rmse_train = np.sqrt(mean_squared_error(y_train, lr_pred_train))
    lr_mae_test = mean_absolute_error(y_test, lr_pred_test)
    lr_mae_train = mean_absolute_error(y_train, lr_pred_train)
    print(f"Linear Regression -> Train R²: {lr_r2_train:.4f}, Test R²: {lr_r2_test:.4f}")
    print(f"Linear Regression -> Train RMSE: {lr_rmse_train:.2f}, Test RMSE: {lr_rmse_test:.2f}")
    print(f"Linear Regression -> Train MAE: {lr_mae_train:.2f}, Test MAE: {lr_mae_test:.2f}")

    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train_log)
    rf_pred_test_log = rf.predict(X_test)
    rf_pred_train_log = rf.predict(X_train)
    # Convert predictions back to original scale
    rf_pred_test = np.expm1(rf_pred_test_log)
    rf_pred_train = np.expm1(rf_pred_train_log)
    # Metrics for Random Forest
    rf_r2_test = r2_score(y_test, rf_pred_test)
    rf_r2_train = r2_score(y_train, rf_pred_train)
    rf_rmse_test = np.sqrt(mean_squared_error(y_test, rf_pred_test))
    rf_rmse_train = np.sqrt(mean_squared_error(y_train, rf_pred_train))
    rf_mae_test = mean_absolute_error(y_test, rf_pred_test)
    rf_mae_train = mean_absolute_error(y_train, rf_pred_train)
    print(f"Random Forest -> Train R²: {rf_r2_train:.4f}, Test R²: {rf_r2_test:.4f}")
    print(f"Random Forest -> Train RMSE: {rf_rmse_train:.2f}, Test RMSE: {rf_rmse_test:.2f}")
    print(f"Random Forest -> Train MAE: {rf_mae_train:.2f}, Test MAE: {rf_mae_test:.2f}")

    # Choose the better model based on Test R² score
    if rf_r2_test > lr_r2_test:
        best_model = rf
        best_model_name = "Random Forest"
        best_test_r2 = rf_r2_test
        best_test_rmse = rf_rmse_test
        best_test_mae = rf_mae_test
    else:
        best_model = lr
        best_model_name = "Linear Regression"
        best_test_r2 = lr_r2_test
        best_test_rmse = lr_rmse_test
        best_test_mae = lr_mae_test
    print(f"\nSelected model: {best_model_name} (Test R²: {best_test_r2:.4f})")

    # Ensure the models directory exists
    model_dir = os.path.join(script_dir, '..', '..', 'models')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # Save the best model
    model_path = os.path.join(model_dir, 'price_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)

    # Save the training columns (for one-hot encoding consistency)
    columns_path = os.path.join(model_dir, 'feature_columns.pkl')
    with open(columns_path, 'wb') as f:
        pickle.dump(training_columns, f)

    print("Model and feature columns saved successfully.")

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
    # Load the model and feature columns
    model_path = os.path.join(script_dir, '..', '..', 'models', 'price_model.pkl')
    columns_path = os.path.join(script_dir, '..', '..', 'models', 'feature_columns.pkl')

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    with open(columns_path, 'rb') as f:
        training_columns = pickle.load(f)

    # Prepare the input data as a DataFrame with the same columns as training
    # Start with the numerical features
    input_data = pd.DataFrame({
        'NoOfBedrooms': [bedrooms],
        'NoOfBathrooms': [bathrooms],
        'AreaSqYards': [area]
    })
    # Create a one-hot encoded column for the address (with the prefix 'Address_')
    address_column = f'Address_{address}'
    # Add the address column, initialize to 0
    input_data[address_column] = 1
    # Ensure all training columns are present, fill missing with 0
    for col in training_columns:
        if col not in input_data.columns:
            input_data[col] = 0
    # Reorder columns to match training order
    input_data = input_data[training_columns]

    # Make prediction (in log space)
    predicted_price_log = model.predict(input_data)[0]
    # Convert back to original price scale
    predicted_price = np.expm1(predicted_price_log)

    return predicted_price

if __name__ == "__main__":
    train_and_save_model()