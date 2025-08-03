import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import pandas as pd
import json
from google import genai
from google.genai import types

# Initialize Gemini client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'
gemini_client = genai.Client(
    http_options=types.HttpOptions(api_version="v1beta1"),
    vertexai=True,
    project='sqy-prod',
    location='global'
)

gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# Streamlit app title and description
st.title("Latest News Summaries")
st.write("Fetches and summarizes news from Construction World, Economic Times Realty, and Realty Plus.")

# Extract news_type and date using Gemini
def extract_names_from_text(text: str) -> dict:
    try:
        if not text:
            return {
                "news_type": "Unknown",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        prompt = f"""
        You are an agent that extracts information from news text. Determine the news type in one or two words 
        (e.g., 'civic', 'real estate', 'govt development'). Return the result in JSON format:
        {{"news_type": "type"}}

        This is raw text: {text}
        """
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=100,
                system_instruction="Extract the news type in one or two words from the provided text.",
                temperature=0.7,
            )
        )
        result = json.loads(response.text)
        return {
            "news_type": result.get("news_type", "Unknown"),
            "date": datetime.now().strftime("%Y-%m-%d")  # Replace with actual date extraction if available
        }
    except Exception as e:
        print(f"Error extracting news_type: {e}")
        return {
            "news_type": "Unknown",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

# Extract city and locality using Gemini
def get_city(text: str) -> dict:
    try:
        if not text:
            return {"city": ["unknown"], "locality": ["unknown"]}
        prompt = f"""
        Extract the city and localities mentioned in the news.
        - If not clearly mentioned, return ["unknown"] for that field.
        - Return city and locality as separate lists in a JSON object.
        - Do not combine them into a single list.

        Respond strictly in the following JSON format:
        {{"city": ["city_1", "city_2"], "locality": ["locality_1", "locality_2"]}}

        **Example Outputs:**
        1. If content mentions: *Gurgaon, Sector 45 and Sector 56*
           {{"city": ["Gurgaon"], "locality": ["Sector 45", "Sector 56"]}}
        2. If content mentions: *Delhi*
           {{"city": ["Delhi"], "locality": ["unknown"]}}
        3. If no city/locality mentioned:
           {{"city": ["unknown"], "locality": ["unknown"]}}

        This is raw text: {text}
        """
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=300,
                system_instruction="Extract city and locality names into separate lists.",
                temperature=0.7,
            )
        )
        result = json.loads(response.text)
        city = result.get("city", ["unknown"])
        locality = result.get("locality", ["unknown"])
        # Ensure "unknown" is returned if lists are empty or contain only "unknown"
        city = city if city and "unknown" not in [x.lower() for x in city] else ["unknown"]
        locality = locality if locality and "unknown" not in [x.lower() for x in locality] else ["unknown"]
        return {"city": city, "locality": locality}
    except Exception as e:
        print(f"Error extracting city/locality: {e}")
        return {"city": ["unknown"], "locality": ["unknown"]}

# Fetch and extract text for constructionworld.in
def fetch_and_extract_text_constructionworld(url: str) -> str:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.select_one('#content > div > div.mobile-banner')
        if element is None:
            print(f"No content found for {url}: Selector returned None")
            return None
        text = element.get_text()
        remove_space = text.replace("\n", '')
        result_text = re.sub(r"[\([{})\]]", "", remove_space)
        return result_text.strip() if result_text.strip() else None
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None

# Fetch and extract text for rprealtyplus.com
def fetch_and_extract_text_realtyplus(url: str) -> str:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.select_one('body > div.col-md-12.p-0 > div.container.mb-4.stry-mt.mob-p-0 > div > div.col-md-8.rightSidebar.mob-p-0 > div > div > div:nth-child(4) > div')
        if element is None:
            print(f"No content found for {url}: Selector returned None")
            return None
        text = element.get_text()
        remove_space = text.replace("\n", '')
        result_text = re.sub(r"[\([{})\]]", "", remove_space)
        return result_text.strip() if result_text.strip() else None
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None

# Generate summary using Gemini
def generate_summary(text: str, url: str) -> dict:
    try:
        if not text:
            return {
                "summary": "Unable to generate summary due to missing content",
                "city": ["unknown"],
                "locality": ["unknown"],
                "news_type": "Unknown",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        extracted_data = extract_names_from_text(text)
        city_locality = get_city(text)
        prompt = f"""
        This is raw text: {text}
        """
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=300,
                system_instruction="You are a news summarization agent. Generate a clear, concise news summary in 20–25 words using the provided text. Focus on key facts only.",
                temperature=0.7,
            )
        )
        summary = response.text.replace("```html", "").replace("```", "")
        return {
            "summary": summary,
            "city": city_locality["city"],
            "locality": city_locality["locality"],
            "news_type": extracted_data.get("news_type", "Unknown"),
            "date": extracted_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        }
    except Exception as e:
        print(f"Error generating summary for {url}: {e}")
        return {
            "summary": f"Error generating summary: {str(e)}",
            "city": ["unknown"],
            "locality": ["unknown"],
            "news_type": "Unknown",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

# Function to fetch and process news
def fetch_news():
    news_items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    # 1. Scrape from constructionworld.in
    url = "https://www.constructionworld.in"
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            target_divs = soup.find_all(class_=["sidebg", "col-lg-4 col-md-12 col-sm-12 col-12"])
            all_urls = []
            for div in target_divs:
                links = div.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        if not href.startswith('http'):
                            href = f"{url}/{href.lstrip('/')}"
                        all_urls.append(href)
            
            valid_urls = 0
            for news_url in all_urls:
                if valid_urls >= 20:
                    break
                text = fetch_and_extract_text_constructionworld(news_url)
                if text:
                    result = generate_summary(text, news_url)
                    news_items.append({
                        "news_url": news_url,
                        "summary": result["summary"],
                        "city": result["city"],
                        "locality": result["locality"],
                        "news_type": result["news_type"],
                        "date": result["date"]
                    })
                    valid_urls += 1
    except Exception as e:
        print(f"Error scraping {url}: {e}")

    # 2. Scrape from realty.economictimes.indiatimes.com RSS
    url = "https://realty.economictimes.indiatimes.com/rss/topstories"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'xml')
        guid_elements = soup.find_all("guid")
        all_urls = [guid.text for guid in guid_elements]
        
        valid_urls = 0
        for news_url in all_urls:
            if valid_urls >= 10:
                break
            try:
                guid_response = requests.get(news_url, timeout=15)
                guid_response.raise_for_status()
                soup = BeautifulSoup(guid_response.text, 'html.parser')
                text_data = soup.get_text()
                final_result = text_data.replace("\n", '')
                description = re.sub(r"[\([{})\]]", "", final_result)
                text = description.strip()
                if text:
                    result = generate_summary(text, news_url)
                    news_items.append({
                        "news_url": news_url,
                        "summary": result["summary"],
                        "city": result["city"],
                        "locality": result["locality"],
                        "news_type": result["news_type"],
                        "date": result["date"]
                    })
                    valid_urls += 1
            except Exception as e:
                print(f"Error processing {news_url}: {e}")
                continue
    except Exception as e:
        print(f"Error scraping {url}: {e}")

    # 3. Scrape from rprealtyplus.com
    url = "https://www.rprealtyplus.com/news-views.html"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        all_urls = []
        for link in links:
            href = link.get('href')
            if href and href.startswith("news-views"):
                full_url = "https://www.rprealtyplus.com/" + href
                if full_url not in all_urls:
                    all_urls.append(full_url)
        
        valid_urls = 0
        for news_url in all_urls:
            if valid_urls >= 6:
                break
            text = fetch_and_extract_text_realtyplus(news_url)
            if text:
                result = generate_summary(text, news_url)
                news_items.append({
                    "news_url": news_url,
                    "summary": result["summary"],
                    "city": result["city"],
                    "locality": result["locality"],
                    "news_type": result["news_type"],
                    "date": result["date"]
                })
                valid_urls += 1
    except Exception as e:
        print(f"Error scraping {url}: {e}")

    return news_items

# Main app logic
if st.button("Fetch Latest News"):
    with st.spinner("Fetching and summarizing news... Please wait."):
        news_items = fetch_news()
        if news_items:
            # Convert to DataFrame for display
            df = pd.DataFrame(news_items, columns=["news_url", "summary", "city", "locality", "news_type", "date"])
            st.subheader("News Summaries")
            # Display table with clickable URLs
            df['news_url'] = df['news_url'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')
            st.write(df.to_html(escape=False), unsafe_allow_html=True)
        else:
            st.warning("No news items fetched. Please try again.")

# Display JSON response
if st.checkbox("Show JSON Response"):
    with st.spinner("Fetching JSON response... Please wait."):
        news_items = fetch_news()
        st.json({"news": news_items})