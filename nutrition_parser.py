import json

def load_foundation_foods(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    
    foods = data.get("FoundationFoods", [])
    parsed_foods = []

    for item in foods:
        food_name = item.get("description", "Unknown Food")
        nutrients = item.get("foodNutrients", [])
        
        macros = {
            "Protein": 0.0,
            "Carbohydrate": 0.0,
            "Total lipid (fat)": 0.0,
            "Energy": 0.0  # aka calories
        }

        for nutrient in nutrients:
            name = nutrient.get("nutrient", {}).get("name", "")
            amount = nutrient.get("amount", 0.0)
            if name in macros:
                macros[name] = amount

        parsed_foods.append({
            "name": food_name,
            "protein": macros["Protein"],
            "carbs": macros["Carbohydrate"],
            "fat": macros["Total lipid (fat)"],
            "calories": macros["Energy"]
        })

    return parsed_foods