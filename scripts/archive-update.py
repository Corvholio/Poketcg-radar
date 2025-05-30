import shutil

# Files to copy
cards_source = "data/latest/pokemon_cards_full_info.csv"
cards_target = "data/archive/pokemon_cards_full_info_2025-05-25.csv"

sets_source = "data/latest/pokemon_sets_summary.csv"
sets_target = "data/archive/pokemon_sets_summary_2025-05-25.csv"

# Copy files
shutil.copy(cards_source, cards_target)
shutil.copy(sets_source, sets_target)

print(f"Archived latest files to May 25th timestamp.")
 