from fastapi import APIRouter
from ..ml.price_model import predict_price

router = APIRouter()

@router.post("/predict-price")
async def predict_price_endpoint(data: dict):
    """
    Predict the price of a property based on its features.
    Expects JSON with keys: address (string), bedrooms (int), bathrooms (int), area (float)
    Returns: {"predicted_price": value}
    """
    address = data.get("address")
    bedrooms = data.get("bedrooms")
    bathrooms = data.get("bathrooms")
    area = data.get("area")

    # Validate input
    if address is None or bedrooms is None or bathrooms is None or area is None:
        return {"error": "Missing required fields: address, bedrooms, bathrooms, area"}

    try:
        # Convert to appropriate types
        bedrooms = float(bedrooms)
        bathrooms = float(bathrooms)
        area = float(area)
    except ValueError:
        return {"error": "Invalid input types. Bedrooms, bathrooms, and area must be numbers."}

    # Call the predict_price function
    predicted_price = predict_price(address, bedrooms, bathrooms, area)

    return {"predicted_price": predicted_price}