import os
import sys
import re
import json
import urllib.parse
import streamlit as st
import openai
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
ga_measurement_id = os.getenv("GA_MEASUREMENT_ID") # Get the GA ID
AMAZON_AFFILIATE_TAG = "aisouschef-20"

# --- SAMPLE RESPONSE FOR TEST MODE ---
SAMPLE_RESPONSE = """
Of course! Here is a sample response.
[RECIPE_START]
# Sample Healthy Cookies
This is a sample recipe for healthy cookies that demonstrates the app's functionality without making a real API call.
### Ingredients
- 1 cup **[Bob's Red Mill Gluten-Free Flour]**
- 1/2 cup **[365 Whole Foods Market Organic Maple Syrup]**
- 1/4 cup Coconut Oil
- 1 tsp Vanilla Extract
### Instructions
1. Mix all ingredients in a bowl.
2. Form into cookie shapes on a baking sheet.
3. Bake at 350°F (175°C) for 12-15 minutes.
[RECIPE_END]
"""

# --- FUNCTIONS ---
def get_ai_suggestion(recipe_text, user_action):
    prompt = f"""
    You are an "AI Sous Chef," a helpful assistant for home cooks.
    Your task is to modify a recipe based on a user's request.
    First, write a brief, friendly introductory sentence or two.
    Then, provide the complete recipe.
    IMPORTANT: Enclose the entire recipe portion (from the title to the last instruction) inside [RECIPE_START] and [RECIPE_END] tags.

    When you suggest a specific type of ingredient or tool that can be purchased,
    please format it like this: **[Product Brand or Type]**.

    Here is the user's recipe:
    ---
    {recipe_text}
    ---

    Here is the user's request: "{user_action}"
    """
    try:
        response = openai.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": "You are an AI Sous Chef."}, {"role": "user", "content": prompt}], temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"

def insert_affiliate_links(text, tag):
    pattern = r"\*\*\[(.*?)\]\*\*"
    def replace_with_link(match):
        search_term = match.group(1).replace(" ", "+")
        link = f"https://www.amazon.com/s?k={search_term}&tag={tag}"
        return f"[{match.group(1)}]({link})"
    return re.sub(pattern, replace_with_link, text)

def extract_recipe_part(full_response):
    try:
        recipe_text = re.search(r"\[RECIPE_START\](.*)\[RECIPE_END\]", full_response, re.DOTALL).group(1)
        intro_text = full_response.split("[RECIPE_START]")[0]
        return intro_text.strip(), recipe_text.strip()
    except AttributeError:
        return "", full_response

# --- STREAMLIT APP ---
st.set_page_config(page_title="AI Sous Chef", layout="wide")

# --- Google Analytics Tracking Code ---
if ga_measurement_id:
    ga_script = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_measurement_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_measurement_id}');
    </script>
    """
    st.components.v1.html(ga_script, height=0)

st.title("🍳 AI Sous Chef")
st.write("Paste a recipe, choose an action, and let the AI help you perfect it!")

if 'recipe_text' not in st.session_state:
    st.session_state.recipe_text = ""
    st.session_state.intro_text = ""

is_dev_mode = os.getenv("DEV_MODE") == "true"
is_test_mode = False
if is_dev_mode:
    is_test_mode = st.checkbox("Run in Test Mode (No API Call)")

actions = [
    "Make this recipe healthier", "Make this recipe vegan", "Make this recipe gluten-free",
    "Find a substitute for an ingredient...", "Halve this recipe", "Double this recipe",
    "Explain a cooking technique...", "Adapt this oven recipe for an air fryer"
]
selected_action = st.selectbox("What would you like to do?", actions)

additional_input = ""
if selected_action in ["Find a substitute for an ingredient...", "Explain a cooking technique..."]:
    additional_input = st.text_input(label="Please specify the ingredient or technique:", placeholder="e.g., butter, folding")

recipe_input = st.text_area("Paste your recipe here:", height=250, placeholder="e.g., Classic Chocolate Chip Cookies...")

col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Get Suggestion ✨"):
        if not is_test_mode and not api_key:
            st.error("Error: OPENAI_API_KEY not found.")
        elif not recipe_input.strip():
            st.error("Please paste a recipe first!")
        else:
            if is_test_mode:
                ai_response = SAMPLE_RESPONSE
                st.session_state.intro_text, st.session_state.recipe_text = extract_recipe_part(ai_response)
            else:
                final_action = selected_action
                if additional_input:
                    final_action = f"{selected_action.replace('...','')} for: {additional_input}"
                
                with st.spinner("Your AI Sous Chef is thinking..."):
                    ai_response = get_ai_suggestion(recipe_input, final_action)
                    st.session_state.intro_text, st.session_state.recipe_text = extract_recipe_part(ai_response)

with col2:
    if st.button("Start Over"):
        st.session_state.recipe_text = ""
        st.session_state.intro_text = ""
        st.rerun()

if st.session_state.recipe_text:
    recipe_with_links = insert_affiliate_links(st.session_state.recipe_text, AMAZON_AFFILIATE_TAG)
    
    if st.session_state.intro_text:
        st.markdown(st.session_state.intro_text)

    st.markdown("---")
    
    st.markdown("### Here's your recipe:")
    st.markdown(recipe_with_links)
    
    st.markdown("---")
    st.text_area("Copy recipe text below:", st.session_state.recipe_text, height=150)