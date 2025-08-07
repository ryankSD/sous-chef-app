import os
import re
import streamlit as st
import openai
from dotenv import load_dotenv
from recipe_scrapers import scrape_me

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# AMAZON_AFFILIATE_TAG has been removed.

# --- SAMPLE RESPONSE FOR TEST MODE ---
SAMPLE_RESPONSE = """
Hello there! I've made this recipe healthier for you. Here's a summary of the changes:
[RECIPE_START]
# Sample Healthy Cookies
- **Servings:** 24 cookies
- **Prep Time:** 10 minutes
- **Cook Time:** 15 minutes
- **Total Time:** 25 minutes
- **Adapted from Sample Recipes:** https://www.example.com
### Ingredients
- 1 cup of a high-quality gluten-free flour
- 1/2 cup of maple syrup
### Instructions
1. Mix all ingredients in a bowl.
2. Bake at 350°F (175°C) for 12-15 minutes.
[RECIPE_END]
"""

# --- FUNCTIONS ---
def format_time(minutes):
    """Converts total minutes into a more readable 'X hours Y minutes' format."""
    if not minutes or not isinstance(minutes, int) or minutes < 1: return None
    hours, mins = divmod(minutes, 60)
    if hours > 0 and mins > 0: return f"{hours} hours {mins} minutes"
    elif hours > 0: return f"{hours} hours"
    else: return f"{mins} minutes"

def scrape_recipe_from_url(url):
    """Scrapes recipe data from a URL and returns it as formatted text."""
    try:
        scraper = scrape_me(url)
        recipe_text = f"# {scraper.title()}\n\n"
        if scraper.yields(): recipe_text += f"- **Servings:** {scraper.yields()}\n"
        if prep_time := format_time(scraper.prep_time()): recipe_text += f"- **Prep Time:** {prep_time}\n"
        if cook_time := format_time(scraper.cook_time()): recipe_text += f"- **Cook Time:** {cook_time}\n"
        if total_time := format_time(scraper.total_time()): recipe_text += f"- **Total Time:** {total_time}\n"
        recipe_text += f"- **Adapted from {scraper.title()}:** {url}\n\n"
        recipe_text += "## Ingredients\n"
        for ingredient in scraper.ingredients(): recipe_text += f"- {ingredient}\n"
        recipe_text += "\n## Instructions\n"
        for instruction in scraper.instructions_list(): recipe_text += f"- {instruction}\n"
        return recipe_text, None
    except Exception:
        error_message = f"The recipe on '{url}' doesn't support URL import. Please copy the recipe and paste it into the 'Paste Recipe' tab."
        return None, error_message

def get_ai_suggestion(recipe_text, user_action, additional_input=""):
    """Generates a tailored prompt for the AI based on the user's action."""
    
    # --- PROMPT ENGINEERING ---
    # Default prompt for general modifications
    prompt_template = f"""
    You are an "AI Sous Chef," a helpful and friendly assistant for home cooks. Your suggestions should be for generic ingredients, not specific brands.
    Your task is to modify a recipe based on a user's request.

    First, write a friendly and encouraging introductory sentence.
    Then, provide a section titled "**Summary of Changes:**" that explains exactly what you changed and why. Use a bulleted list.
    After the summary, provide the complete, modified recipe.

    IMPORTANT: The instructions section of the recipe MUST be a single, continuous numbered list (1., 2., 3.).

    Enclose the entire recipe portion (from the title to the last instruction) inside [RECIPE_START] and [RECIPE_END] tags.

    Here is the user's recipe:
    ---
    {recipe_text}
    ---
    Here is the user's request: "{user_action}"
    """

    # Specific prompt for explaining a technique
    if "Explain a cooking technique" in user_action:
        prompt_template = f"""
        You are an "AI Sous Chef," a helpful and clear cooking instructor.
        A user has asked for an explanation of a specific cooking technique from a recipe they are reading.
        Provide a clear, concise, and easy-to-understand explanation of the requested technique. Do not include a recipe.

        Here is the user's recipe for context:
        ---
        {recipe_text}
        ---
        Here is the user's request: "Explain the technique: {additional_input}"
        """

    # Specific prompt for finding a substitute
    elif "Find a substitute for an ingredient" in user_action:
        prompt_template = f"""
        You are an "AI Sous Chef," an expert in ingredient substitutions. Your suggestions should be for generic ingredients, not specific brands.
        Your task is to modify a recipe to substitute a specific ingredient.

        First, write a friendly introductory sentence.
        Then, provide a section titled "**Substitution Details:**". In this section, state the exact substitution you made in the new recipe. Then, provide a bulleted list of other possible substitutions that the user could also consider.
        
        After the details, provide the complete, modified recipe featuring the substitution.
        
        IMPORTANT: The instructions section of the recipe MUST be a single, continuous numbered list (1., 2., 3.).

        Enclose the entire recipe portion (from the title to the last instruction) inside [RECIPE_START] and [RECIPE_END] tags.

        Here is the user's recipe:
        ---
        {recipe_text}
        ---
        Here is the user's request: "Find a substitute for: {additional_input}"
        """

    try:
        response = openai.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": "You are an AI Sous Chef."}, {"role": "user", "content": prompt_template}], temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"

# The insert_affiliate_links function has been removed.

def extract_recipe_part(full_response):
    try:
        recipe_text = re.search(r"\[RECIPE_START\](.*)\[RECIPE_END\]", full_response, re.DOTALL).group(1)
        intro_text = full_response.split("[RECIPE_START]")[0]
        return intro_text.strip(), recipe_text.strip()
    except AttributeError:
        # If tags are not found, it's likely an explanation-only response
        return full_response, None

# --- STREAMLIT APP ---
st.set_page_config(page_title="AI Sous Chef", layout="wide")
st.title("🍳 AI Sous Chef")

# Initialize session state
if 'recipe_text' not in st.session_state:
    st.session_state.recipe_text = ""
    st.session_state.intro_text = ""
    st.session_state.error_message = None
    st.session_state.scrape_failed = False

# --- Main App Logic ---

# STATE 1: SCRAPE FAILED
if st.session_state.scrape_failed:
    st.error(st.session_state.error_message)
    if st.button("⬅️ Start Over"):
        st.session_state.recipe_text = ""
        st.session_state.intro_text = ""
        st.session_state.error_message = None
        st.session_state.scrape_failed = False
        st.rerun()

# STATE 2: DISPLAY RESULTS
elif st.session_state.recipe_text or st.session_state.intro_text:
    if st.button("⬅️ Start Over"):
        st.session_state.recipe_text = ""
        st.session_state.intro_text = ""
        st.session_state.error_message = None
        st.session_state.scrape_failed = False
        st.rerun()

    # Display the explanation/intro part
    if st.session_state.intro_text:
        st.markdown(st.session_state.intro_text)

    # Display the recipe part if it exists
    if st.session_state.recipe_text:
        # We no longer need to process for affiliate links
        st.markdown("---")
        st.markdown("### Here's your recipe:")
        st.markdown(st.session_state.recipe_text)
        st.markdown("---")
        st.text_area("Copy recipe text below:", st.session_state.recipe_text, height=150)
    
    st.markdown("---")
    st.markdown("Found a bug or have an idea? [**Give us your feedback!**](https://docs.google.com/forms/d/e/1FAIpQLSfLbMN6fzkWvZJCF07WEwxDAFsR5Umv_caU7cfHBbgh0DjN6g/viewform?usp=header)")

# STATE 3: INPUT FORM
else:
    st.write("Paste a recipe or import from a URL, choose an action, and let the AI help you perfect it!")
    input_method_tab, url_tab = st.tabs(["Paste Recipe", "Import from URL"])
    
    with input_method_tab:
        recipe_text_area = st.text_area("Paste your recipe here:", height=300, placeholder="e.g., Classic Chocolate Chip Cookies...")
    with url_tab:
        url_input = st.text_input("Enter a recipe URL:", placeholder="https://www.allrecipes.com/...")

    actions = ["Make this recipe healthier", "Make this recipe vegan", "Make this recipe gluten-free", "Find a substitute for an ingredient...", "Halve this recipe", "Double this recipe", "Explain a cooking technique...", "Adapt this oven recipe for an air fryer"]
    selected_action = st.selectbox("What would you like to do?", actions)
    
    additional_input = ""
    if selected_action == "Find a substitute for an ingredient...":
        additional_input = st.text_input(label="Please specify the ingredient:", placeholder="e.g., butter, flour, eggs")
    elif selected_action == "Explain a cooking technique...":
        additional_input = st.text_input(label="Please specify the technique:", placeholder="e.g., folding, searing, blanching")

    is_dev_mode = os.getenv("DEV_MODE") == "true"
    is_test_mode = False 
    if is_dev_mode:
        is_test_mode = st.checkbox("Run in Test Mode (No API Call)")

    if st.button("Get Suggestion ✨"):
        recipe_input_source = None
        if recipe_text_area.strip():
            recipe_input_source = recipe_text_area
        elif url_input.strip():
            with st.spinner("Scraping recipe from URL..."):
                recipe_input_source, error = scrape_recipe_from_url(url_input)
                if error:
                    st.session_state.error_message = error
                    st.session_state.scrape_failed = True
                    st.rerun()
        
        if not recipe_input_source or not recipe_input_source.strip():
            if not st.session_state.scrape_failed:
                st.error("Please paste a recipe or provide a valid URL first!")
        elif not is_test_mode and not api_key:
            st.error("Error: OPENAI_API_KEY not found.")
        else:
            if is_test_mode:
                ai_response = SAMPLE_RESPONSE
                st.session_state.intro_text, st.session_state.recipe_text = extract_recipe_part(ai_response)
                st.rerun()
            else:
                final_action = selected_action
                if additional_input:
                    final_action = f"{selected_action.replace('...','')} for: {additional_input}"
                with st.spinner("Your AI Sous Chef is thinking..."):
                    ai_response = get_ai_suggestion(recipe_input_source, final_action, additional_input)
                    st.session_state.intro_text, st.session_state.recipe_text = extract_recipe_part(ai_response)
                    st.rerun()