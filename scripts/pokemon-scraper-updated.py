import os
import requests
import pandas as pd
import time
import ast
from datetime import datetime
import urllib.parse

def extract_avg(stats):
    if isinstance(stats, str):
        try:
            stats = ast.literal_eval(stats)
        except:
            stats = []
    if isinstance(stats, list) and stats:
        avg = stats[0].get('avg')
        return avg if avg is not None else 0
    return 0

def get_all_sets():
    url = "https://www.pokedata.io/_next/data/3UYacdm8ZflJ3oxZlMwiK/sets.json"
    response = requests.get(url)
    data = response.json()
    sets = data['pageProps']['setInfoArr']
    return sets

def get_cards_for_set(set_name, set_id):
    encoded_set_name = urllib.parse.quote(set_name)
    url = f"https://www.pokedata.io/api/cards?set_name={encoded_set_name}"
    
    attempts = 0
    while attempts < 2:  # Try twice if 0 cards
        response = requests.get(url)
        if response.status_code == 200:
            cards = response.json()
            if cards and len(cards) > 0:
                print(f"✅ Successfully fetched {len(cards)} cards for {set_name}", flush=True)
                return cards
            else:
                attempts += 1
                if attempts < 2:
                    print(f"⚠️ Fetched 0 cards for {set_name}, retrying in 10 minutes...", flush=True)
                    time.sleep(10 * 60)
                else:
                    print(f"⚠️ Skipping {set_name} after 2 attempts with 0 cards.", flush=True)
                    return []
        else:
            print(f"⚠️ Failed to fetch data for {set_name} (Status {response.status_code}), retrying in 10 minutes...", flush=True)
            time.sleep(10 * 60)

def save_data():
    os.makedirs("data/latest", exist_ok=True)
    os.makedirs("data/archive", exist_ok=True)
    
    sets = get_all_sets()
    total_sets = len(sets)
    all_cards = []
    sets_summary = []

    for idx, s in enumerate(sets, start=1):
        set_name = s.get('name')
        set_id = s.get('id')
        print(f"[{idx}/{total_sets}] Fetching cards for set: {set_name} (ID: {set_id})", flush=True)
        cards = get_cards_for_set(set_name, set_id)
        if cards:
            for c in cards:
                c['Price'] = round(extract_avg(c.get('stats', [])), 2)  # Final clean Price column
            all_cards.extend(cards)
            total_cards = len(cards)
            total_value = sum(c['Price'] for c in cards)
            sets_summary.append({
                "Set Name": set_name,
                "Set ID": set_id,
                "Total Cards": total_cards,
                "Total Estimated Value": total_value
            })

    cards_df = pd.DataFrame(all_cards)
    sets_df = pd.DataFrame(sets_summary)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    cards_df.to_csv("data/latest/pokemon_cards_full_info.csv", index=False)
    sets_df.to_csv("data/latest/pokemon_sets_summary.csv", index=False)
    print("✅ Latest datasets saved.", flush=True)

    cards_df.to_csv(f"data/archive/pokemon_cards_full_info_{timestamp}.csv", index=False)
    sets_df.to_csv(f"data/archive/pokemon_sets_summary_{timestamp}.csv", index=False)
    print("✅ Archive copies saved.", flush=True)

    hist_file = "data/pokemon_price_history.csv"
    price_column = f"Price_{timestamp}"
    if os.path.exists(hist_file):
        hist_df = pd.read_csv(hist_file)
        latest_prices = cards_df[['id', 'name', 'set_name', 'Price']].rename(columns={'Price': price_column})
        hist_df = pd.merge(hist_df, latest_prices, on=['id', 'name', 'set_name'], how='outer')
    else:
        hist_df = cards_df[['id', 'name', 'set_name', 'Price']].rename(columns={'Price': price_column})
    
    hist_df.to_csv(hist_file, index=False)
    print("✅ Historical price tracking updated.", flush=True)

if __name__ == "__main__":
    save_data()

