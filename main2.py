from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
import os
import uvicorn

# Load Google credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './sqy-prod.json'

# Initialize Gemini client
gemini_client = genai.Client(
    http_options=genai.types.HttpOptions(api_version="v1beta1"),
    vertexai=True,
    project='sqy-prod',
    location='global'
)

# Google Search tool for Gemini
gemini_tools = [types.Tool(google_search=types.GoogleSearch())]

# FastAPI app
app = FastAPI(title="Civic & Infrastructure News API")

class NewsItem(BaseModel):
    city: Optional[str] = None
    summary: str
    locality: Optional[str] = None
    source: Optional[str] = None
    news_type: Optional[str] = None
    date: str

class NewsResponse(BaseModel):
    news: List[NewsItem]

# Prompt template
def build_prompt(city: str) -> str:
    return f"""
Fetch at least 10 local civic and infrastructure news updates published today for the following Indian city: {city}.

Only include news reported today. If no such news exists, return nothing (null or empty).

Limit news to those that concern specific localities or neighborhoods, and that fall under these categories:

- New infrastructure developments or government projects (initiated or inaugurated)
- Urban or transport planning announcements (roads, metro, sewage, expressways, etc.)
- Road conditions, traffic disruptions, flooding, or damage
- Water supply, drainage, or sewage problems
- Public safety, electricity, or civic security concerns

For each relevant story, return in the following format:
{{
  "news": [
    {{
      "city": "City name",
      "summary": "Short news summary here",
      "locality": "Location",
      "source": "News source",
      "news_type": "Metro/Water/etc.",
      "date": "2025-08-03"
    }}
  ]
}}

Exclude any older or unrelated topics.
""".strip()

@app.get("/news", response_model=NewsResponse)
async def get_city_news(city: str = Query(..., description="Enter the city name")):
    try:
        final_prompt = build_prompt(city)

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=final_prompt,
            config=genai.types.GenerateContentConfig(
                tools=gemini_tools,
                max_output_tokens=2000,
                temperature=0.7,
                system_instruction="You are a civic news agent. Only return news published today. If no fresh news is available, return nothing.",
            )
        )

        result_text = response.text.strip()
        print(result_text)
        if not result_text or result_text.lower() in ["null", "none", "no news", "no fresh news"]:
            return {"news": []}

        # Naive line-by-line parsing (for structured responses; improve with regex/json later)
        lines = [line for line in result_text.splitlines() if line.strip()]
        parsed_news = []
        current = {}

        for line in lines:
            lower = line.lower()
            value = line.split(":", 1)[-1].strip().strip('",')
            if "summary" in lower:
                if current: parsed_news.append(current)
                current = {"summary": value, "city": city}
            elif "locality" in lower:
                current["locality"] = value
            elif "source" in lower:
                current["source"] = value
            elif "news_type" in lower:
                current["news_type"] = value
            elif "date" in lower:
                current["date"] = value
        if current: parsed_news.append(current)
        # print(parsed_news)
        return {"news": parsed_news}

    except Exception as e:
        return {"news": [], "error": str(e)}

# To run: uvicorn filename:app --reload