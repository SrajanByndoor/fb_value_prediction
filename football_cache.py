import sqlite3
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "football_data.db"
CACHE_TTL_HOURS = 24


def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT,
            short_name TEXT,
            tla TEXT,
            crest TEXT
        )
    """)

    # Matches table - optimized for ML features
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            utc_date TEXT,
            status TEXT,
            matchday INTEGER,
            stage TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            home_halftime INTEGER,
            away_halftime INTEGER,
            winner TEXT,
            season_id INTEGER,
            season_start_year INTEGER,
            competition_code TEXT,
            last_updated TEXT,
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        )
    """)

    # API cache for raw responses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            endpoint TEXT PRIMARY KEY,
            response_json TEXT,
            cached_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def is_cache_valid(cached_at_str):
    """Check if cache is still valid based on TTL."""
    if not cached_at_str:
        return False
    cached_at = datetime.fromisoformat(cached_at_str)
    return datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS)


def get_cached_response(endpoint):
    """Get cached API response if valid."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT response_json, cached_at FROM api_cache WHERE endpoint = ?",
        (endpoint,)
    )
    row = cursor.fetchone()
    conn.close()

    if row and is_cache_valid(row["cached_at"]):
        print(f"[CACHE HIT] {endpoint}")
        return json.loads(row["response_json"])
    return None


def save_to_cache(endpoint, response_json):
    """Save API response to cache."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO api_cache (endpoint, response_json, cached_at)
        VALUES (?, ?, ?)
    """, (endpoint, json.dumps(response_json), datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_team(cursor, team_data):
    """Save or update team data."""
    cursor.execute("""
        INSERT OR REPLACE INTO teams (id, name, short_name, tla, crest)
        VALUES (?, ?, ?, ?, ?)
    """, (
        team_data["id"],
        team_data["name"],
        team_data.get("shortName"),
        team_data.get("tla"),
        team_data.get("crest")
    ))


def save_match(cursor, match_data, competition_code):
    """Save or update match data."""
    score = match_data.get("score", {})
    full_time = score.get("fullTime", {})
    half_time = score.get("halfTime", {})

    # Extract season start year from season startDate
    season_start = match_data["season"].get("startDate", "")
    season_start_year = int(season_start[:4]) if season_start else None

    cursor.execute("""
        INSERT OR REPLACE INTO matches (
            id, utc_date, status, matchday, stage,
            home_team_id, away_team_id,
            home_score, away_score,
            home_halftime, away_halftime,
            winner, season_id, season_start_year, competition_code, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match_data["id"],
        match_data["utcDate"],
        match_data["status"],
        match_data["matchday"],
        match_data["stage"],
        match_data["homeTeam"]["id"],
        match_data["awayTeam"]["id"],
        full_time.get("home"),
        full_time.get("away"),
        half_time.get("home"),
        half_time.get("away"),
        score.get("winner"),
        match_data["season"]["id"],
        season_start_year,
        competition_code,
        match_data["lastUpdated"]
    ))


def fetch_and_cache_matches(competition="PL", season=None, api_token=None):
    """Fetch matches from API with caching.

    Args:
        competition: Competition code (e.g., "PL" for Premier League)
        season: Season year (e.g., 2023 for 2023-24 season). None for current.
        api_token: API authentication token
    """
    endpoint = f"https://api.football-data.org/v4/competitions/{competition}/matches"
    if season:
        endpoint += f"?season={season}"

    # Check cache first
    cached = get_cached_response(endpoint)
    if cached:
        return cached

    # Fetch from API
    print(f"[API CALL] {endpoint}")
    headers = {}
    if api_token:
        headers["X-Auth-Token"] = api_token

    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Save raw response to cache
    save_to_cache(endpoint, data)

    # Extract and save normalized data
    conn = get_connection()
    cursor = conn.cursor()

    for match in data.get("matches", []):
        save_team(cursor, match["homeTeam"])
        save_team(cursor, match["awayTeam"])
        save_match(cursor, match, competition)

    conn.commit()
    conn.close()

    return data


def fetch_historical_seasons(competition="PL", years_back=3, api_token=None):
    """Fetch multiple seasons of historical data.

    Args:
        competition: Competition code
        years_back: Number of past seasons to fetch
        api_token: API authentication token

    Returns:
        Total number of matches fetched
    """
    current_year = datetime.now().year
    # If we're before August, current season started last year
    if datetime.now().month < 8:
        current_year -= 1

    total_matches = 0

    for i in range(years_back + 1):  # Include current season
        season_year = current_year - i
        print(f"\n--- Fetching {season_year}-{str(season_year + 1)[2:]} season ---")

        try:
            data = fetch_and_cache_matches(
                competition=competition,
                season=season_year,
                api_token=api_token
            )
            match_count = len(data.get("matches", []))
            total_matches += match_count
            print(f"    {match_count} matches")
        except requests.exceptions.HTTPError as e:
            print(f"    Error: {e}")

    return total_matches


def get_training_data():
    """Get matches formatted for ML training."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            m.id,
            m.utc_date,
            m.matchday,
            m.season_start_year,
            m.home_team_id,
            m.away_team_id,
            ht.name as home_team,
            at.name as away_team,
            m.home_score,
            m.away_score,
            m.home_halftime,
            m.away_halftime,
            m.winner,
            m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'FINISHED'
        ORDER BY m.utc_date
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_training_stats():
    """Get summary statistics of training data."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            season_start_year,
            COUNT(*) as matches,
            SUM(CASE WHEN winner = 'HOME_TEAM' THEN 1 ELSE 0 END) as home_wins,
            SUM(CASE WHEN winner = 'AWAY_TEAM' THEN 1 ELSE 0 END) as away_wins,
            SUM(CASE WHEN winner = 'DRAW' THEN 1 ELSE 0 END) as draws
        FROM matches
        WHERE status = 'FINISHED'
        GROUP BY season_start_year
        ORDER BY season_start_year
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# Initialize database on import
init_db()
