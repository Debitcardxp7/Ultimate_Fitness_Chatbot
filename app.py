import pandas as pd
import cohere
import os
from dotenv import load_dotenv
import streamlit as st
from nutrition_parser import load_foundation_foods

# Load environment variables 
load_dotenv()
cohere_api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(cohere_api_key)

# --- Dataset Loading ---
def load_exercise_data(csv_file):
    df = pd.read_csv(csv_file)
    return df 

exercise_data = load_exercise_data('megaGymDataset.csv') 
foods = load_foundation_foods("data/foundation.json")

# --- Clean nutrition data ---
nutrition_data = nutrition_data[["Food_Item", "Category", "Calories (kcal)",
                                 "Protein (g)", "Carbohydrates (g)", "Fat (g)", "Fiber (g)"
                                 ]].drop_duplicates().reset_index(drop=True)

# --- recommendation function ---
def recommend_foods(goal, food_data, top_n=10):
    if goal == "Build Muscle":
        return food_data[
            (food_data["Calories (kcal)"] > 150) &
            (food_data["Protein (g)"] > 20)
        ].sort_values(by="Calories (kcal)", ascending=False).head(top_n)
    elif goal == "Weight Loss":
        return food_data[
            (food_data["Calories (kcal)"] < 200) &
            (food_data["Protein (g)"] > 10)
        ].sort_values(by="Calories (kcal)", ascending=True).head(top_n)
    elif goal == "Endurance":
        return food_data[
            (food_data["Carbohydrates (g)"] > 30) &
            (food_data["Calories (kcal)"] < 300)
        ].sort_values(by="Carbohydrates (g)", ascending=False).head(top_n)
    else:
        return food_data[
            (food_data["Calories (kcal)"].between(100, 300)) &
            (food_data["Protein (g)"] > 10)
        ].sort_values(by="Calories (kcal)", ascending=False).head(top_n)
# --- Builds Macros ---
def calculate_macros(weight, goal):
    if goal == "Build Muscle":
        protein = weight * 1.5
        carbs = weight * 2.0
        fat = weight * 0.5
        calories = weight * 16
    elif goal == "Weight Loss":
        protein = weight * 1.2
        carbs = weight * 1.0
        fat = weight * 0.3
        calories = weight * 13
    else:  # General Fitness or Endurance
        protein = weight * 1.0
        carbs = weight * 1.5
        fat = weight * 0.4
        calories = weight * 15

    return {
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "calories": calories
    }

# --- Macro Contribution ---
def food_macro_contribution(food):
    return {
        "Food": food["Food_Item"],
        "Calories": food["Calories (kcal)"],
        "Protein (g)": food["Protein (g)"],
        "Carbs (g)": food["Carbohydrates (g)"],
        "Fat (g)": food["Fat (g)"],
        "Fiber (g)": food["Fiber (g)"]
    }

# --- User Preferences ---
def gather_user_preferences():
    goal = st.selectbox("What's your main fitness goal?", 
                        ["Weight Loss", "Build Muscle", "Endurance", "General Fitness"])
    experience = st.radio("What's your experience level?",
                          ["Beginner", "Intermediate", "Advanced"])
    weight = st.number_input("What's your current weight (lbs)?", min_value=50, max_value=500, value=150)
    restrictions = st.checkbox("Any injuries or limitations?")
    return goal, experience, weight, restrictions

# --- Prompt Helper ---
def craft_fitness_prompt(query, exercise_data, weight, macros):
    return (
        f"You know all the core principles of fitness nutrition:\n"
        "- Protein target = 1.0–1.5g per lb of bodyweight for muscle gain\n"
        "- Calorie maintenance = ~15 cal per lb of bodyweight\n"
        "- Macro splits depend on goal:\n"
        "  • Build Muscle = ~35% protein, 45% carbs, 20% fat\n"
        "  • Weight Loss = higher protein, lower carbs\n"
        "- Always give realistic, evidence-based advice — but with sass and roasts.\n"
        "- Never give meal plans that go under 1400 calories.\n\n"
        f"The user asked: '{query}'\n"
        f"They weigh {weight} lbs.\n"
        f"Estimated daily targets:\n"
        f"• Calories: {macros['calories']} kcal\n"
        f"• Protein: {macros['protein']} g\n"
        f"• Carbs: {macros['carbs']} g\n"
        f"• Fat: {macros['fat']} g\n\n"
        "You have access to a dataset where each exercise has:\n"
        "- Title (name)\n"
        "- Description (how to perform it)\n"
        "- Type (e.g., Strength, Cardio)\n"
        "- Body part (e.g., Legs, Arms)\n"
        "- Equipment required (if any)\n"
        "- Difficulty level (Beginner, Intermediate, Advanced)\n"
        "Be creative and roast them while giving advice. Don’t explain the dataset structure, just use it.\n"
    )

# --- Process Chat Query ---
def process_query(query, exercise_data, user_preferences):
    goal, experience, weight, restrictions = user_preferences
    macros = calculate_macros(weight, goal)
    history = "".join([f"User: {chat['user']}\nBot: {chat['bot']}\n" for chat in st.session_state.chat_history])

    prompt = (
        f"{history}\nUser: {query}\n"
        f"{craft_fitness_prompt(query, exercise_data, weight, macros)}"
    )

    response = co.chat(
        model='command-nightly',
        message=prompt,
        temperature=0.7
    )

    return response.text.strip()

# --- Pagination Helper Functions ---

def go_first():
    st.session_state.chat_index = 1

def go_prev():
    st.session_state.chat_index = max(1, st.session_state.chat_index - 1)

def go_next():
    st.session_state.chat_index = min(len(st.session_state.chat_history), st.session_state.chat_index + 1)

def go_last():
    st.session_state.chat_index = len(st.session_state.chat_history)

# --- Initialize State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_index" not in st.session_state:
    st.session_state.chat_index = 1
if "just_submitted" not in st.session_state:
    st.session_state.just_submitted = False

# --- UI ---
st.title("Fitness Guru Bot")
user_preferences = gather_user_preferences()
goal, _, weight, _ = user_preferences
macros = calculate_macros(weight, goal) 

user_input = st.text_input("Ask me about workouts or fitness...")


if st.button("Submit"): 
    if user_input and user_preferences:
        chatbot_response = process_query(user_input, exercise_data, user_preferences)
        st.session_state.chat_history.append({
            "user": user_input,
            "bot": chatbot_response
        })
        st.session_state.chat_index = len(st.session_state.chat_history)
        st.session_state.just_submitted = True
    else:
        st.warning("Please enter a question and set your preferences.")

# --- Chat Display ---
if st.session_state.chat_history:
    chat = st.session_state.chat_history[st.session_state.chat_index - 1]
    st.write(f"**User:** {chat['user']}")
    st.write(f"**Bot:** {chat['bot']}")

    st.markdown("### 🍱 Food Suggestions Based on Your Goal")
    food_df = recommend_foods(goal, nutrition_data)
    contrib_list = []
    for _, row in food_df.iterrows():
        contrib = food_macro_contribution(row, macros)
        contrib["Food"] = row["Food_Item"]
        contrib_list.append(contrib)

    st.dataframe(pd.DataFrame(contrib_list).set_index("Food"), use_container_width=True)
    st.markdown("---")

# --- Pagination Buttons ---
if st.session_state.chat_history:
    col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])

    with col1:
        st.button("First", key="first_btn", on_click=go_first, disabled=st.session_state.chat_index == 1)
    with col2:
        st.button("Previous", key="prev_btn", on_click=go_prev, disabled=st.session_state.chat_index == 1)
    with col3:
        st.write(f"Page {st.session_state.chat_index} of {len(st.session_state.chat_history)}")
    with col4:
        st.button("Next", key="next_btn", on_click=go_next, disabled=st.session_state.chat_index == len(st.session_state.chat_history))
    with col5:
        st.button("Last", key="last_btn", on_click=go_last, disabled=st.session_state.chat_index == len(st.session_state.chat_history))

# --- Reset Flags (at very end) ---
st.session_state.just_submitted = False
