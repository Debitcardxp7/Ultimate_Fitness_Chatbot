import json

# Load your FoundationFoods JSON
with open("data/foundation.json", "r") as f:
    data = json.load(f)

foods = data.get("FoundationFoods", [])

# Nutrients you want to extract
TARGET_NUTRIENTS = {
    "Protein": "protein",
    "Carbohydrate, by difference": "carbs",
    "Total lipid (fat)": "fat",
    "Energy": "calories"
}

extracted_foods = []

for food in foods:  # foods is data['FoundationFoods']
    name = food.get("description", "Unknown Food")
    nutrients = {v: 0.0 for v in TARGET_NUTRIENTS.values()}

    for nutrient_entry in food.get("foodNutrients", []):
        nutrient_info = nutrient_entry.get("nutrient", {})
        nutrient_name = nutrient_info.get("name")
        nutrient_value = nutrient_entry.get("amount")

        if nutrient_name in TARGET_NUTRIENTS and nutrient_value is not None:
            key = TARGET_NUTRIENTS[nutrient_name]
            nutrients[key] = nutrient_value

    extracted_foods.append({
        "name": name,
        **nutrients
    })


# Print a few to check
for f in extracted_foods[:5]:  # Print first 5 foods
    print(f)
