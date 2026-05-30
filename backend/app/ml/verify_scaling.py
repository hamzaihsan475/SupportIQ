from price_model import predict_price

def test_linear_scaling():
    address = "DHA Phase 6"
    bedrooms = 2
    bathrooms = 2
    test_areas = [60, 120, 240]

    print(f"Testing linear scaling for {address}, {bedrooms} Bed, {bathrooms} Bath")
    print("-" * 50)

    results = {}
    for area in test_areas:
        price = predict_price(address, bedrooms, bathrooms, area)
        results[area] = price
        print(f"Area: {area} sq yards -> Predicted Price: {price:,.2f}")

    # Mathematical Verification
    # Ratio 60:120 should be 0.5
    ratio_60_120 = results[60] / results[120]
    # Ratio 120:240 should be 0.5
    ratio_120_240 = results[120] / results[240]

    print("-" * 50)
    print(f"Ratio (60/120): {ratio_60_120:.4f} (Expected: 0.5000)")
    print(f"Ratio (120/240): {ratio_120_240:.4f} (Expected: 0.5000)")

    if abs(ratio_60_120 - 0.5) < 1e-5 and abs(ratio_120_240 - 0.5) < 1e-5:
        print("\nSUCCESS: Linear scaling verified.")
    else:
        print("\nFAILURE: Linear scaling is not behaving as expected.")

if __name__ == "__main__":
    test_linear_scaling()
