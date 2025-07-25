import pandas as pd
import cohere
import os
import time
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

# --- Nutrition Data Loading ---
@st.cache_data
def load_nutrition_data():
    return pd.read_parquet("data/foundation.parquet")

# --- Load nutrition data with spinner ---
with st.spinner("Loading food nutrition data... hang tight!"):
    nutrition_data = load_nutrition_data()


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

# New: Filter exercises based on goal and experience
def filter_exercises(exercise_data, goal, experience):
    # Map fitness goals to exercise types or body parts (customize as needed)
    goal_map = {
        "Build Muscle": ["Strength", "Hypertrophy"],
        "Weight Loss": ["Cardio", "HIIT"],
        "Endurance": ["Cardio", "Endurance"],
        "General Fitness": ["Strength", "Cardio", "Flexibility"]
    }
    exp_levels = {
        "Beginner": ["Beginner"],
        "Intermediate": ["Beginner", "Intermediate"],
        "Advanced": ["Beginner", "Intermediate", "Advanced"]
    }

    filtered = exercise_data[
        (exercise_data["Type"].isin(goal_map.get(goal, []))) &
        (exercise_data["Level"].isin(exp_levels.get(experience, [])))
    ]

    # Return top 5 exercises as a sample
    return filtered.head(5)

# Modify craft_fitness_prompt to include exercise summary
def craft_fitness_prompt(query, weight, macros, filtered_exercises):
    exercise_list_text = "\n".join(
        [f"- {row['Title']}: {row['Desc']}" for _, row in filtered_exercises.iterrows()]
    )
    return (
        f"You are a snarky but accurate fitness coach. Always base your advice on science and user's goals.\n\n"
        f"User weight: {weight} lbs\n"
        f"Daily macro targets:\n"
        f"• Calories: {macros['calories']} kcal\n"
        f"• Protein: {macros['protein']} g\n"
        f"• Carbs: {macros['carbs']} g\n"
        f"• Fat: {macros['fat']} g\n\n"
        "Recommended exercises for the user based on their goal and experience:\n"
        f"{exercise_list_text}\n\n"
        "Don't explain datasets. Give tough love. Be funny but informative. No fluff. Never give a meal plan under 1400 kcal.\n"
    )

# Update process_query to accept user preferences and incorporate exercise filtering
def process_query(user_input, chat, weight, macros, goal, experience):
    filtered_exercises = filter_exercises(exercise_data, goal, experience)
    full_chat = [
        {"role": "SYSTEM", "message": craft_fitness_prompt("", weight, macros, filtered_exercises)},
    ]
    if chat:
        full_chat.extend([
            {"role": "USER", "message": chat["user"]},
            {"role": "CHATBOT", "message": chat["bot"]},
        ])

    response = co.chat(
        model="command-nightly",
        chat_history=full_chat,
        message=user_input,
        temperature=0.7,
    )
    return response.text

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
        with st.spinner("Thinking super hard..."):
            chatbot_response = process_query(
                user_input,
                st.session_state.chat_history[-1] if st.session_state.chat_history else None,
                weight,
                macros,
                goal,
                user_preferences[1]  # experience
            )
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

    st.markdown("### Food Suggestions Based on Your Goal")
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
