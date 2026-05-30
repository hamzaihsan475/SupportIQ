import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import pickle
import os

def standardize_address(address: str) -> str:
    """
    Standardize address to match training dataset tokens.
    """
    if not address or not isinstance(address, str):
        return "other"

    addr_lower = address.lower()
    if 'dha' in addr_lower or 'defence' in addr_lower:
        return 'DHA Phase 6, DHA Defence'
    if 'bahria' in addr_lower:
        return 'Bahria Town Karachi, Karachi'
    if 'gulshan' in addr_lower:
        return 'Gulshan-e-Iqbal, Karachi'

    return address

def train_and_save_model():
    # Load the data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '..', '..', 'data', 'Cleaned_Data.csv')
    df = pd.read_csv(csv_path)

    if 'Unnamed: 0' in df.columns:
        df = df.drop('Unnamed: 0', axis=1)

    # Compute global median price for fallback
    median_price = df['Price'].median()

    # Prepare features and target
    X = df[['Address', 'NoOfBedrooms', 'NoOfBathrooms']]
    y = df['Price']

    y_log = np.log1p(y)

    # One-hot encode the Address column
    X = pd.get_dummies(X, columns=['Address'], prefix='Address', drop_first=False)

    # Split the data
    X_train, X_test, y_train_log, y_test_log = train_test_split(X, y_log, test_size=0.2, random_state=42)

    training_columns = X_train.columns.tolist()

    # Train Linear Regression
    lr = LinearRegression()
    lr.fit(X_train, y_train_log)
    lr_pred_test_log = lr.predict(X_test)
    lr_pred_train_log = lr.predict(X_train)
    lr_pred_test = np.expm1(lr_pred_test_log)
    lr_pred_train = np.expm1(lr_pred_train_log)
    y_train = np.expm1(y_train_log)
    y_test = np.expm1(y_test_log)
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
    rf_pred_test = np.expm1(rf_pred_test_log)
    rf_pred_train = np.expm1(rf_pred_train_log)
    rf_r2_test = r2_score(y_test, rf_pred_test)
    rf_r2_train = r2_score(y_train, rf_pred_train)
    rf_rmse_test = np.sqrt(mean_squared_error(y_test, rf_pred_test))
    rf_rmse_train = np.sqrt(mean_squared_error(y_train, rf_pred_train))
    rf_mae_test = mean_absolute_error(y_test, rf_pred_test)
    rf_mae_train = mean_absolute_error(y_train, rf_pred_train)
    print(f"Random Forest -> Train R²: {rf_r2_train:.4f}, Test R²: {rf_r2_test:.4f}")
    print(f"Random Forest -> Train RMSE: {rf_rmse_train:.2f}, Test RMSE: {rf_rmse_test:.2f}")
    print(f"Random Forest -> Train MAE: {rf_mae_train:.2f}, Test MAE: {rf_mae_test:.2f}")

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

    model_dir = os.path.join(script_dir, '..', '..', 'models')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    model_path = os.path.join(model_dir, 'price_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)

    columns_path = os.path.join(model_dir, 'feature_columns.pkl')
    with open(columns_path, 'wb') as f:
        pickle.dump(training_columns, f)

    median_path = os.path.join(model_dir, 'median_price.pkl')
    with open(median_path, 'wb') as f:
        pickle.dump(median_price, f)

    print("Model, feature columns, and median price saved successfully.")

def predict_price(address, bedrooms, bathrooms, area):
    """
    Predict the price of a property based on its features with address standardization and fallback.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, '..', '..', 'models', 'price_model.pkl')
    columns_path = os.path.join(script_dir, '..', '..', 'models', 'feature_columns.pkl')
    median_path = os.path.join(script_dir, '..', '..', 'models', 'median_price.pkl')

    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(columns_path, 'rb') as f:
        training_columns = pickle.load(f)
    with open(median_path, 'rb') as f:
        median_price = pickle.load(f)

    std_address = standardize_address(address)

    input_data = pd.DataFrame({
        'NoOfBedrooms': [bedrooms],
        'NoOfBathrooms': [bathrooms]
    })

    address_column = f'Address_{std_address}'
    input_data[address_column] = 1

    for col in training_columns:
        if col not in input_data.columns:
            input_data[col] = 0

    input_data = input_data[training_columns]

    # Check if the address was found in training columns
    address_found = f'Address_{std_address}' in training_columns

    # Make prediction (in log space)
    predicted_price_log = model.predict(input_data)[0]
    predicted_price = np.expm1(predicted_price_log)

    if not address_found:
        # Fallback logic: use median price as baseline and apply tier multiplier
        baseline = median_price
        multiplier = 1.0

        addr_lower = address.lower()
        if 'dha' in addr_lower or 'defence' in addr_lower:
            multiplier = 1.3
        elif 'bahria' in addr_lower or 'gulshan' in addr_lower:
            multiplier = 1.0
        elif 'dalmia' in addr_lower:
            multiplier = 0.7

        predicted_price = baseline * multiplier

    # Deterministic post-processing for scaling
    area_ratio = area / 120
    bedroom_adjustment = 1 + 0.05 * (bedrooms - 2)
    final_price = predicted_price * area_ratio * bedroom_adjustment

    return final_price

if __name__ == "__main__":
    train_and_save_model()

    # Verification tests
    test_cases = [
        ("Dha", 3, 2, 250),
        ("Dalmia", 3, 2, 250),
        ("bahria town", 3, 2, 250)
    ]

    print("\n--- Verification Predictions ---")
    for addr, bed, bath, area in test_cases:
        price = predict_price(addr, bed, bath, area)
        print(f"Input: {addr}, Bed: {bed}, Bath: {bath}, Area: {area} -> Predicted Price: {price:,.2f}")
