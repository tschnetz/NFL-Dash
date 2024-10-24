# api.py
from datetime import datetime
from fastapi import FastAPI
import requests
from config import HEADERS, NFL_EVENTS_URL, ODDS_URL, SCOREBOARD_URL, SCORING_PLAYS_URL

app = FastAPI()

@app.get("/nfl-events")
def fetch_nfl_events():
    querystring = {"year": "2024"}
    response = requests.get(NFL_EVENTS_URL, headers=HEADERS, params=querystring)
    if response.status_code == 200:
        return response.json()
    return {"error": "Failed to fetch NFL events"}

@app.get("/nfl-eventodds")
def fetch_espn_bet_odds(game_id: str, game_status: str):
    querystring = {"id": game_id}
    response = requests.get(ODDS_URL, headers=HEADERS, params=querystring)
    if response.status_code == 200:
        odds_data = response.json()
        for item in odds_data.get('items', []):
            if item.get('provider', {}).get('id') == "58":  # ESPN BET Provider ID
                return item.get('details', 'N/A')
    return {"error": "Failed to fetch odds"}

@app.get("/nfl-scoreboard-day")
def fetch_games_by_day():
    today = datetime.now().strftime('%Y%m%d')
    querystring = {"day": today}
    response = requests.get(SCOREBOARD_URL, headers=HEADERS, params=querystring)
    if response.status_code == 200:
        return response.json()
    return {"error": "Failed to fetch games"}

@app.get("/nfl-scoringplays")
def get_scoring_plays(game_id: str):
    querystring = {"id": game_id}
    response = requests.get(SCORING_PLAYS_URL, headers=HEADERS, params=querystring)
    if response.status_code == 200:
        return response.json().get('scoringPlays', [])
    return {"error": "Failed to fetch scoring plays"}