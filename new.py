import streamlit as st
from google import genai
from google.genai import types
import os

# Load Google credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'

# Initialize Gemini client
gemini_client = genai.Client(
    http_options=genai.types.HttpOptions(api_version="v1beta1"),
    vertexai=True,
    project='sqy-prod',
    location='global'
)

# Add Google Search tool
gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# Default editable prompt (Today’s civic news only)
default_prompt = """
Fetch at least 10 local civic and infrastructure news updates published today for the following Indian cities:
Gurgaon
Noida
Delhi
Greater Noida
Mumbai
Thane
Navi Mumbai
Pune
Hyderabad
Bangalore 
Chennai

Only include news reported today. If no such news exists, return nothing (null or empty).

Limit news to those that concern specific localities or neighborhoods, and that fall under these categories:

- New infrastructure developments or government projects (initiated or inaugurated)
- Urban or transport planning announcements (roads, metro, sewage, expressways, etc.)
- Road conditions, traffic disruptions, flooding, or damage
- Water supply, drainage, or sewage problems
- Public safety, electricity, or civic security concerns

For each relevant story:
- Mention the city and locality/neighborhood (if available)
- Summarize the issue/development clearly
- Include the reporting date (must be today)
- Add a reliable source link

Exclude any older or unrelated topics.
"""

# Streamlit UI
st.title("📍 Civic & Infrastructure News Fetcher")
st.write("Gemini will fetch **today’s** verified civic news using Google Search.")

prompt_input = st.text_area("📝 Edit or customize the news-fetching prompt:", value=default_prompt, height=400)

if st.button("🔍 Fetch News"):
    if not prompt_input.strip():
        st.warning("Please enter a valid prompt.")
    else:
        with st.spinner("Fetching today's news using Gemini + Google Search..."):
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite-preview-06-17",
                    contents=prompt_input.strip(),
                    config=genai.types.GenerateContentConfig(
                        tools=gemini_tools,
                        max_output_tokens=2000,
                        temperature=0.7,
                        system_instruction="You are a civic news agent. Only return news published today. If no fresh news is available, return nothing.",
                    )
                )

                result = response.text.strip().lower()

                # Handle "no news" cases
                if result in ["none", "null", "no news found", "no recent news", "no fresh news available", "no news available today"]:
                    st.info("🚫 No civic news found for today.")
                else:
                    st.success("✅ Latest Civic News for Today:")
                    st.markdown(response.text.strip())

            except Exception as e:
                st.error(f"❌ Error: {e}")
