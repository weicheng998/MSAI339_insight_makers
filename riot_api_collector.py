import requests
import time
import json

# --- Configuration ---
# IMPORTANT: Replace with your own Riot API key. Remember it expires every 24 hours!
API_KEY = "RGAPI-REPLACE" 
# The region to query. See Riot API docs for all available regions.
# Americas routing value for match-v5 is 'americas', Europe is 'europe', Asia is 'asia'
REGION_V4 = "na1"  # North America for league-v4, summoner-v4
REGION_V5 = "americas" # Routing value for match-v5

# --- Headers for API Requests ---
HEADERS = {
    "X-Riot-Token": API_KEY
}

# --- Main Functions ---

def get_challenger_players(queue='RANKED_SOLO_5x5'):
    """Gets the list of Challenger players for a given queue."""
    print("Fetching Challenger players...")
    url = f"https://{REGION_V4}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/{queue}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        league_list = response.json()
        
        # Extract PUUIDs from the list of players
        puuids = [player['puuid'] for player in league_list['entries']]
        print(f"Successfully fetched {len(puuids)} Challenger player PUUIDs.")
        return puuids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching challenger players: {e}")
        return []

def get_match_ids(puuid, count=20):
    """Gets a list of recent match IDs for a given player PUUID."""
    print(f"Fetching match IDs for PUUID: {puuid[:20]}...")
    url = f"https://{REGION_V5}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    
    # IMPORTANT: Respect rate limits. This simple delay helps a lot.
    time.sleep(1.5) 
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        match_ids = response.json()
        print(f"Found {len(match_ids)} match IDs.")
        return match_ids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching match IDs for PUUID {puuid}: {e}")
        return []

def get_match_data(match_id):
    """Gets detailed data for a single match ID."""
    print(f"Fetching data for match: {match_id}")
    url = f"https://{REGION_V5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    
    # IMPORTANT: Respect rate limits.
    time.sleep(1.5)

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # If a single match fails, we can skip it and continue
        print(f"Error fetching data for match {match_id}: {e}")
        return None

# --- Main Execution Logic ---
if __name__ == "__main__":
    # 1. Get a list of Challenger player PUUIDs
    challenger_puuids = get_challenger_players()
    
    if challenger_puuids:
        all_match_ids = set() # Use a set to avoid duplicate match IDs

        # 2. Get match histories for the top N players to gather match IDs
        # Let's just do the top 5 players to not send too many requests at once.
        # You can increase this number for your project.
        for puuid in challenger_puuids[:5]: 
            match_ids = get_match_ids(puuid)
            all_match_ids.update(match_ids)
        
        print(f"\nCollected a total of {len(all_match_ids)} unique match IDs to analyze.")
        
        all_match_data = []
        
        # 3. Get detailed data for each unique match
        for match_id in list(all_match_ids):
            match_data = get_match_data(match_id)
            if match_data:
                all_match_data.append(match_data)
        
        print(f"\nSuccessfully collected data for {len(all_match_data)} matches.")
        
        # 4. Now you have the data!
        # For this example, we'll just print the info of the first match collected.
        # In your project, you would save `all_match_data` to a file (e.g., JSON or CSV).
        if all_match_data:
            print("\n--- Example Data from First Match ---")
            first_match = all_match_data[0]
            print(f"Game Version: {first_match['info']['gameVersion']}")
            print("Participants' Champion Names:")
            for participant in first_match['info']['participants']:
                print(f"- {participant['championName']}")

        if all_match_data:
            # Save the entire list of match data to a single file
            file_path = "lol_match_data.json"
            print(f"\nSaving data for {len(all_match_data)} matches to {file_path}...")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_match_data, f, ensure_ascii=False, indent=4)
                
            print("Data saved successfully!")