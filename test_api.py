from football_cache import fetch_historical_seasons, get_training_data, get_training_stats

API_TOKEN = "52dcaec4b25044758b411a631f774bac"

# Fetch 3 years of historical data + current season
total = fetch_historical_seasons(competition="PL", years_back=3, api_token=API_TOKEN)
print(f"\n{'='*50}")
print(f"Total matches fetched: {total}")

# Get training data stats by season
print(f"\n{'='*50}")
print("Training Data by Season:")
print(f"{'='*50}")
stats = get_training_stats()
for s in stats:
    season = f"{s['season_start_year']}-{str(s['season_start_year'] + 1)[2:]}"
    print(f"{season}: {s['matches']} matches | H:{s['home_wins']} A:{s['away_wins']} D:{s['draws']}")

# Total training samples
training_data = get_training_data()
print(f"\n{'='*50}")
print(f"Total training samples: {len(training_data)}")
print(f"{'='*50}")