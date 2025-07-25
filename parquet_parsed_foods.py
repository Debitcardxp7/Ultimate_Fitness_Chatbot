import pandas as pd
from nutrition_parser import load_foundation_foods

# Load foundation foods and save as Parquet
# One time Script
foods = load_foundation_foods("data/foundation.json")

df = pd.DataFrame(foods).rename(columns={
    "name": "Food_Item",
    "protein": "Protein (g)",
    "carbs": "Carbohydrates (g)",
    "fat": "Fat (g)",
    "calories": "Calories (kcal)"
})
df.to_parquet("data/foundation.parquet")
print("Saved as Parquet")