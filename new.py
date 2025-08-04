import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from google import genai
from google.genai import types

# Streamlit page configuration
st.set_page_config(page_title="Civic & Infrastructure News", layout="wide")

# Load Google credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'

# Initialize Gemini client
try:
    gemini_client = genai.Client(
        http_options=genai.types.HttpOptions(api_version="v1beta1"),
        vertexai=True,
        project='sqy-prod',
        location='global'
    )
except Exception as e:
    st.error(f"Failed to initialize Gemini client: {str(e)}")
    st.stop()

# Google Search tool for Gemini
gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# NewsItem class for structured data
class NewsItem:
    def __init__(self, city: str, summary: str, locality: str = None, source: str = None, news_type: str = None, date: str = None):
        self.city = city
        self.summary = summary
        self.locality = locality
        self.source = source
        self.news_type = news_type
        self.date = date

# Default prompt template
def get_default_prompt(city: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""
Fetch at least 10 local civic and infrastructure news updates published on or after {today} for the following Indian city: {city}.

If no such news exists, return an empty JSON array: [].

Limit news to those that concern specific localities or neighborhoods, and that fall under these categories:

- New infrastructure developments or government projects (initiated or inaugurated)
- Urban or transport planning announcements (roads, metro, sewage, expressways, etc.)
- Road conditions, traffic disruptions, flooding, or damage
- Water supply, drainage, or sewage problems
- Public safety, electricity, or civic security concerns

For each relevant story, return in the following JSON format:
[
  {{
    "city": "City name",
    "summary": "Short news summary here",
    "locality": "Location",
    "source": "News source",
    "news_type": "Metro/Water/etc.",
    "date": "YYYY-MM-DD"
  }}
]

Exclude any unrelated topics.
""".strip()

# Title and description
st.title("Civic & Infrastructure News Updates")
st.markdown("Select an Indian city and customize the prompt to fetch today's civic and infrastructure news updates.")

# City selection dropdown
cities = [
    "Gurgaon", "Noida", "Delhi", "Greater Noida", "Mumbai", 
    "Thane", "Navi Mumbai", "Pune", "Hyderabad", "Bangalore", "Chennai"
]
city = st.selectbox("Select City", options=[""] + cities, index=0, help="Choose a city to fetch news for.")

# Prompt editing
st.subheader("Customize Prompt (Optional)")
default_prompt = get_default_prompt("{city}")  # Placeholder for city
prompt = st.text_area(
    "Edit Prompt",
    value=default_prompt,
    height=300,
    help="Modify the prompt sent to the Gemini API. Use {city} as a placeholder for the selected city."
)

# Disable button if no city is selected
fetch_button = st.button("Fetch News", disabled=not city)

if fetch_button:
    if not city:
        st.error("Please select a city.")
    else:
        # Replace {city} in the prompt with the selected city
        final_prompt = prompt.replace("{city}", city)
        
        with st.spinner("Fetching news..."):
            try:
                # Fetch news from Gemini API
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite-preview-06-17",
                    contents=final_prompt,
                    config=genai.types.GenerateContentConfig(
                        tools=gemini_tools,
                        max_output_tokens=2000,
                        temperature=0.7,
                        system_instruction="You are a civic news agent. Only return news published today in JSON format. If no fresh news is available, return an empty JSON array: [].",
                    )
                )

                result_text = response.text.strip()
                # Debugging: Display raw response (optional, can be commented out)
                # st.write("Debug: Gemini API response:", result_text)

                if not result_text or result_text.lower() in ["null", "none", "no news", "no fresh news", "[]"]:
                    st.warning(f"No civic or infrastructure news found for {city} today.")
                else:
                    try:
                        # Parse JSON response
                        cleaned_text = result_text.strip().strip("```json").strip("```")
                        news_list = json.loads(cleaned_text) if cleaned_text else []
                        if not isinstance(news_list, list):
                            st.error("Invalid response format from server.")
                        elif not news_list:
                            st.warning(f"No civic or infrastructure news found for {city} today.")
                        else:
                            # Convert to list of NewsItem objects
                            parsed_news = [
                                NewsItem(
                                    city=item.get("city", city),
                                    summary=item.get("summary", ""),
                                    locality=item.get("locality"),
                                    source=item.get("source"),
                                    news_type=item.get("news_type"),
                                    date=item.get("date", datetime.now().strftime("%Y-%m-%d"))
                                )
                                for item in news_list
                                if item.get("summary")
                            ]

                            # Convert to DataFrame for display
                            df = pd.DataFrame([vars(item) for item in parsed_news]).fillna("N/A")
                            st.success(f"Found {len(df)} news items for {city}!")

                            # Display news in a table
                            st.subheader(f"News for {city}")
                            st.dataframe(
                                df[["city", "summary", "locality", "news_type", "source", "date"]],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "city": "City",
                                    "summary": "Summary",
                                    "locality": "Locality",
                                    "news_type": "News Type",
                                    "source": "Source",
                                    "date": "Date"
                                }
                            )

                            # Display each news item in an expandable section
                            for idx, news in enumerate(parsed_news, 1):
                                with st.expander(f"News Item {idx}: {news.summary[:50]}..."):
                                    st.write(f"**City:** {news.city}")
                                    st.write(f"**Summary:** {news.summary}")
                                    st.write(f"**Locality:** {news.locality or 'N/A'}")
                                    st.write(f"**News Type:** {news.news_type or 'N/A'}")
                                    st.write(f"**Source:** {news.source or 'N/A'}")
                                    st.write(f"**Date:** {news.date}")
                    except json.JSONDecodeError as e:
                        st.error(f"Error parsing news data: {str(e)}")
            except Exception as e:
                st.error(f"Error fetching news: {str(e)}")

# Footer
st.markdown("---")
# st.markdown("Powered by Google Gemini API | Built with Streamlit")