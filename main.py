from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
import requests
import os

app = FastAPI()

class TextRequest(BaseModel):
    text: str

class LocationRequest(BaseModel):
    latitude: float
    longitude: float

class BookRequest(BaseModel):
    title: str

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.environ["MY_API_KEY"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.post("/echo")
def echo_text(request: TextRequest):
    return {"you_sent": request.text, "length": len(request.text)}

@app.post("/summarize")
def summarize_text(request: TextRequest, auth: None = Depends(verify_api_key)):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": f"Summarize this in one sentence: {request.text}"}
        ]
    }
    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        return {"error": "Failed to get summary", "details": response.json()}

    data = response.json()
    summary = data["choices"][0]["message"]["content"]
    return {"summary": summary}

@app.post("/weather-advice")
def weather_advice(request: LocationRequest):
    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "current": "temperature_2m,precipitation,wind_speed_10m"
    }
    weather_response = requests.get(weather_url, params=params)

    if weather_response.status_code != 200:
        return {"error": "Failed to fetch weather", "details": weather_response.text}

    weather_data = weather_response.json()
    current = weather_data["current"]

    openai_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"The current temperature is {current['temperature_2m']}°C, "
        f"precipitation is {current['precipitation']}mm, "
        f"and wind speed is {current['wind_speed_10m']} km/h. "
        f"Give a short, friendly recommendation on what to wear or bring outside."
    )
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    openai_response = requests.post(openai_url, headers=headers, json=body)

    if openai_response.status_code != 200:
        return {"error": "Failed to get advice", "details": openai_response.json()}

    advice = openai_response.json()["choices"][0]["message"]["content"]

    return {
        "raw_weather": current,
        "advice": advice
    }

@app.post("/book-summary")
def book_summary(request: BookRequest, auth: None = Depends(verify_api_key)):
    search_url = "https://openlibrary.org/search.json"
    search_response = requests.get(search_url, params={"q": request.title})

    if search_response.status_code != 200:
        return {"error": "Failed to search books", "details": search_response.text}

    search_data = search_response.json()
    if not search_data["docs"]:
        return {"error": "No books found for that title"}

    first_result = search_data["docs"][0]
    work_key = first_result["key"]
    found_title = first_result["title"]

    work_url = f"https://openlibrary.org{work_key}.json"
    work_response = requests.get(work_url)

    if work_response.status_code != 200:
        return {"error": "Failed to fetch work details", "details": work_response.text}

    work_data = work_response.json()
    author_key = work_data["authors"][0]["author"]["key"]

    author_url = f"https://openlibrary.org{author_key}.json"
    author_response = requests.get(author_url)

    if author_response.status_code != 200:
        return {"error": "Failed to fetch author details", "details": author_response.text}

    author_data = author_response.json()
    author_name = author_data["name"]

    openai_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }
    prompt = f"In one short, friendly sentence, recommend the book '{found_title}' by {author_name} to a potential reader."
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    openai_response = requests.post(openai_url, headers=headers, json=body)

    if openai_response.status_code != 200:
        return {"error": "Failed to get recommendation", "details": openai_response.json()}

    recommendation = openai_response.json()["choices"][0]["message"]["content"]

    return {
        "title": found_title,
        "author": author_name,
        "recommendation": recommendation
    }