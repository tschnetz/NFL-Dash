# config.py
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
NFL_EVENTS_URL = "https://nfl-api-data.p.rapidapi.com/nfl-events"
ODDS_URL = "https://nfl-api-data.p.rapidapi.com/nfl-eventodds"
SCORING_PLAYS_URL = "https://nfl-api-data.p.rapidapi.com/nfl-scoringplays"
SCOREBOARD_URL = "https://nfl-api-data.p.rapidapi.com/nfl-scoreboard-day"
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "nfl-api-data.p.rapidapi.com"
}
ODDS_FILE_PATH = 'last_fetched_odds.json'
PORT = int(os.environ.get('PORT', 8080))