import os
import requests
import pandas as pd
from datetime import datetime
import time

# Constants
DATA_FOLDER = "data"
ARCHIVE_FOLDER = "archive"
SETS_URL = "https://raw.githubusercontent.com/nicholas/poketcg-radar/main/data/pokemon_sets_summary.csv"
CARDS_BASE_URL = "https://www.pokedata.io/api/cards?set_name={}"

# Ensure folders exist
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

# Load sets
sets_df = pd.read_csv(SETS_URL)

# Collect data for all sets
all_cards = []
for index, row in sets_df.iterrows():
    set_name = row['name']
    set_id = row['id']
    print(f"Fetching cards for set: {set_name} (ID: {set_id})")
    retry_count = 0

    while True:
        try:
            response = requests.get(CARDS_BASE_URL.format(set_name.replace(' ', '+')))
            if response.status_code == 200:
                cards = response.json()
                for card in cards:
                    all_cards.append(card)
                print(f"✅ Successfully fetched {len(cards)} cards for {set_name}")
                break
            elif response.status_code == 429:
                retry_count += 1
                wait_minutes = 10
                print(f"⚠️ Rate limit encountered for {set_name} (Attempt {retry_count}). Waiting {wait_minutes} minutes before retry.")
                time.sleep(wait_minutes * 60)
            else:
                print(f"❌ Failed to fetch data for {set_name}. Status code: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Error fetching data for {set_name}: {e}")
            retry_count += 1
            wait_minutes = 10
            print(f"Waiting {wait_minutes} minutes before retry.")
            time.sleep(wait_minutes * 60)

# Convert to DataFrame
cards_df = pd.DataFrame(all_cards)

# Save latest data
latest_cards_file = os.path.join(DATA_FOLDER, "pokemon_cards_full_info.csv")
cards_df.to_csv(latest_cards_file, index=False)
print(f"✅ Latest data saved to {latest_cards_file}")

# Save archive
timestamp = datetime.now().strftime("%Y-%m-%d")
archive_cards_file = os.path.join(ARCHIVE_FOLDER, f"pokemon_cards_full_info_{timestamp}.csv")
cards_df.to_csv(archive_cards_file, index=False)
print(f"✅ Archived data saved to {archive_cards_file}")
