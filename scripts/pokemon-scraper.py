import requests
import pandas as pd
from tqdm import tqdm
import time
import sys
import os
from datetime import datetime

# Configurable parameters
MAX_RETRIES = 5
TIMEOUT = 10
DEFAULT_DELAY = 5
WAIT_LONG = 600
DATA_DIR = "data"
LATEST_DIR = os.path.join(DATA_DIR, "latest")
TODAY_DIR = os.path.join(DATA_DIR, datetime.now().strftime("%Y-%m-%d"))
SETS_FILE_LATEST = os.path.join(LATEST_DIR, "pokemon_sets_summary.csv")
CARDS_FILE_LATEST = os.path.join(LATEST_DIR, "pokemon_cards_full_info.csv")
PRICE_HISTORY_FILE = os.path.join(DATA_DIR, "pokemon_price_history.csv")

# Ensure directories exist
os.makedirs(LATEST_DIR, exist_ok=True)
os.makedirs(TODAY_DIR, exist_ok=True)

# Load existing data
if os.path.exists(SETS_FILE_LATEST):
    existing_sets_df = pd.read_csv(SETS_FILE_LATEST)
    existing_set_ids = set(existing_sets_df['Set ID'])
    print("✅ Loaded existing sets.")
else:
    existing_sets_df = pd.DataFrame()
    existing_set_ids = set()
    print("🆕 No existing sets found. Full scrape will run.")

if os.path.exists(CARDS_FILE_LATEST):
    existing_cards_df = pd.read_csv(CARDS_FILE_LATEST)
else:
    existing_cards_df = pd.DataFrame()

if os.path.exists(PRICE_HISTORY_FILE):
    price_history_df = pd.read_csv(PRICE_HISTORY_FILE)
else:
    price_history_df = pd.DataFrame()

# Fetch sets
sets_url = "https://www.pokedata.io/_next/data/3UYacdm8ZflJ3oxZlMwiK/sets.json"
response = requests.get(sets_url, timeout=TIMEOUT)
sets_data = response.json()
sets_list = sets_data['pageProps']['setInfoArr']

all_cards = []
all_set_summaries = []
price_history_records = []
current_date = datetime.now().strftime("%Y-%m-%d")

for set_info in tqdm(sets_list, desc="Processing sets"):
    set_id = set_info['id']
    set_name = set_info['name']
    set_code = set_info.get('code', '')
    series = set_info.get('series', '')
    release_date = set_info.get('release_date', '')
    language = set_info.get('language', '')

    is_new_set = set_id not in existing_set_ids
    print(f"\n📥 Processing set: {set_name} (ID: {set_id}) | {'New' if is_new_set else 'Existing'}")

    cards_data = None
    for attempt in range(MAX_RETRIES):
        try:
            cards_url = f"https://www.pokedata.io/api/cards?set_name={set_name.replace(' ', '+')}&stats=kwan"
            cards_response = requests.get(cards_url, timeout=TIMEOUT)
            if cards_response.status_code == 200:
                cards_data = cards_response.json()
                print(f"✅ Fetched {len(cards_data)} cards for {set_name}")
                break
            elif cards_response.status_code == 429:
                wait_time = (2 ** attempt) * 5
                print(f"⚠️ Attempt {attempt+1}: Rate limit. Waiting {wait_time} sec.")
                for r in range(wait_time, 0, -1):
                    sys.stdout.write(f"\r⏳ Retrying in {r} sec...")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
            else:
                print(f"⚠️ Attempt {attempt+1}: Status {cards_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt+1}: Error {e}")
        time.sleep(2)

    while cards_data is None:
        print(f"⏳ Long wait ({WAIT_LONG//60} min) due to repeated failures.")
        for r in range(WAIT_LONG, 0, -1):
            sys.stdout.write(f"\r⏳ Retrying in {r//60}:{r%60:02d}...")
            sys.stdout.flush()
            time.sleep(1)
        print()
        try:
            cards_response = requests.get(cards_url, timeout=TIMEOUT)
            if cards_response.status_code == 200:
                cards_data = cards_response.json()
                print(f"✅ Fetched after long wait.")
                break
            elif cards_response.status_code == 429:
                print(f"⚠️ Still rate limited. Waiting again.")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error after wait: {e}")

    for card in cards_data:
        card_id = card['id']
        stats = card['stats']
        avg_price = stats[0]['avg'] if stats and stats[0]['avg'] is not None else None

        card_entry = {
            'Card ID': card_id,
            'Set ID': card.get('set_id', set_id),
            'Set Name': set_name,
            'Set Code': card.get('set_code', set_code),
            'Card Name': card['name'],
            'Card Number': card['num'],
            'Language': card['language'],
            'Image URL': card['img_url'],
            'Release Date': card['release_date'],
            f'Price ({current_date})': avg_price
        }
        all_cards.append(card_entry)

        price_record = {
            'Card ID': card_id,
            'Set ID': card.get('set_id', set_id),
            'Set Name': set_name,
            'Card Name': card['name'],
            'Card Number': card['num'],
            'Date': current_date,
            'Price': avg_price
        }
        price_history_records.append(price_record)

    total_cards = len(cards_data)
    total_value = sum(stat[0]['avg'] for card in cards_data if card['stats'] and card['stats'][0]['avg'] is not None for stat in [card['stats']])
    avg_value = total_value / total_cards if total_cards > 0 else 0

    set_summary = {
        'Set ID': set_id,
        'Set Name': set_name,
        'Set Code': set_code,
        'Series': series,
        'Language': language,
        'Release Date': release_date,
        'Total Cards': total_cards,
        'Total Value (Estimated)': total_value,
        'Average Card Value': avg_value
    }
    all_set_summaries.append(set_summary)
    time.sleep(DEFAULT_DELAY)

# Merge and save cards & sets
cards_df = pd.DataFrame(all_cards)
if not existing_cards_df.empty:
    cards_df = pd.merge(existing_cards_df, cards_df, on=['Card ID', 'Set ID', 'Set Name', 'Set Code', 'Card Name', 'Card Number', 'Language', 'Image URL', 'Release Date'], how='outer')

sets_df = pd.DataFrame(all_set_summaries)
cards_df.to_csv(os.path.join(LATEST_DIR, "pokemon_cards_full_info.csv"), index=False)
cards_df.to_csv(os.path.join(TODAY_DIR, "pokemon_cards_full_info.csv"), index=False)
sets_df.to_csv(os.path.join(LATEST_DIR, "pokemon_sets_summary.csv"), index=False)
sets_df.to_csv(os.path.join(TODAY_DIR, "pokemon_sets_summary.csv"), index=False)

# Update master price history
new_price_history_df = pd.DataFrame(price_history_records)
if not price_history_df.empty:
    price_history_df = pd.concat([price_history_df, new_price_history_df], ignore_index=True)
else:
    price_history_df = new_price_history_df
price_history_df.drop_duplicates(subset=['Card ID', 'Date'], inplace=True)
price_history_df.to_csv(PRICE_HISTORY_FILE, index=False)

print(f"\n✅ Data updated: 'latest/', '{TODAY_DIR}', and master price history!")
