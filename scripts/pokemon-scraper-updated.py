import os
import requests
import pandas as pd
import time
import ast
from datetime import datetime

# Extract price from stats field
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

# Fetch all sets
def get_all_sets():
    url = "https://www.pokedata.io/_next/data/3UYacdm8ZflJ3oxZlMwiK/sets.json"
    response = requests.get(url)
    data = response.json()
    sets = data['pageProps']['setInfoArr']
    return sets

# Fetch cards for a set with infinite retry
def get_cards_for_set(set_name, set_id):
    url = f"https://www.pokedata.io/api/cards?set_name={set_name.replace(' ', '+')}"
    while True:
        response = requests.get(url)
        if response.status_code == 200:
            cards = response.json()
            cards_data = []
            for card in cards:
                avg_price = extract_avg(card.get('stats', []))
                card_data = {
                    "hot": card.get("hot"),
                    "id": card.get("id"),
                    "img_url": card.get("img_url"),
                    "language": card.get("language"),
                    "live": card.get("live"),
                    "name": card.get("name"),
                    "num": card.get("num"),
                    "release_date": card.get("release_date"),
                    "secret": card.get("secret"),
                    "set_code": card.get("set_code"),
                    "set_id": card.get("set_id"),
                    "set_name": card.get("set_name"),
                    "Price": avg_price
                }
                cards_data.append(card_data)
            return cards_data
        else:
            print(f"Failed to fetch data for {set_name} (Status {response.status_code}), retrying in 10 minutes...")
            time.sleep(10 * 60)

# Save data to correct folders
def save_data():
    os.makedirs("data/latest", exist_ok=True)
    os.makedirs("data/archive", exist_ok=True)
    
    sets = get_all_sets()
    all_cards = []
    sets_summary = []

    for s in sets:
        set_name = s.get('name')
        set_id = s.get('id')
        print(f"Fetching cards for set: {set_name} (ID: {set_id})")
        cards = get_cards_for_set(set_name, set_id)
        if cards:
            all_cards.extend(cards)
            total_cards = len(cards)
            total_value = sum(c.get('Price', 0) for c in cards)
            sets_summary.append({
                "Set Name": set_name,
                "Set ID": set_id,
                "Total Cards": total_cards,
                "Total Estimated Value": total_value
            })

    # Convert to DataFrames
    cards_df = pd.DataFrame(all_cards)
    sets_df = pd.DataFrame(sets_summary)

    # Save latest data
    timestamp = datetime.now().strftime("%Y-%m-%d")
    cards_df.to_csv("data/latest/pokemon_cards_full_info.csv", index=False)
    sets_df.to_csv("data/latest/pokemon_sets_summary.csv", index=False)
    print("✅ Latest datasets saved.")

    # Save archive copies
    cards_df.to_csv(f"data/archive/pokemon_cards_full_info_{timestamp}.csv", index=False)
    sets_df.to_csv(f"data/archive/pokemon_sets_summary_{timestamp}.csv", index=False)
    print("✅ Archive copies saved.")

    # Update historical prices
    hist_file = "data/pokemon_price_history.csv"
    price_column = f"Price_{timestamp}"
    if os.path.exists(hist_file):
        hist_df = pd.read_csv(hist_file)
        latest_prices = cards_df[['id', 'Price']].rename(columns={'Price': price_column})
        hist_df = pd.merge(hist_df, latest_prices, on='id', how='outer')
    else:
        hist_df = cards_df[['id', 'name', 'set_name', 'Price']].rename(columns={'Price': price_column})

    hist_df.to_csv(hist_file, index=False)
    print("✅ Historical price tracking updated.")

if __name__ == "__main__":
    save_data()
