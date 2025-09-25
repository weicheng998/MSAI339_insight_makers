"""
Riot Games API Data Acquisition Script for Data Science Projects
===============================================================

This script provides functions to acquire data from the Riot Games API
for League of Legends analysis. It includes rate limiting, error handling,
and data export functionality.

Dependencies: requests, pandas, time, json
Usage: Set your API_KEY and call the various data acquisition functions.

Author: Data Science Coursework
Date: September 2025
"""

import requests
import pandas as pd
import json
import time
from typing import Dict, List, Optional, Union
import os
from datetime import datetime
import csv

# Configuration
API_KEY = ""  # Set your Riot API key here
BASE_URL = "https://{region}.api.riotgames.com"

# Rate limiting configuration (Riot API has strict rate limits)
RATE_LIMIT_DELAY = 1.2  # Seconds between API calls
MAX_RETRIES = 3

# Regional endpoints
REGIONS = {
    'na1': 'na1.api.riotgames.com',  # North America
    'euw1': 'euw1.api.riotgames.com',  # Europe West
    'eun1': 'eun1.api.riotgames.com',  # Europe Nordic & East
    'kr': 'kr.api.riotgames.com',  # Korea
    'br1': 'br1.api.riotgames.com',  # Brazil
    'la1': 'la1.api.riotgames.com',  # Latin America North
    'la2': 'la2.api.riotgames.com',  # Latin America South
    'oc1': 'oc1.api.riotgames.com',  # Oceania
    'tr1': 'tr1.api.riotgames.com',  # Turkey
    'ru': 'ru.api.riotgames.com',  # Russia
    'jp1': 'jp1.api.riotgames.com'  # Japan
}

class RiotAPIClient:
    """
    A client for interacting with the Riot Games API with built-in rate limiting
    and error handling.
    """
    
    def __init__(self, api_key: str, region: str = 'na1'):
        """
        Initialize the Riot API client.
        
        Args:
            api_key (str): Your Riot API key
            region (str): Region code (default: 'na1')
        """
        if not api_key:
            raise ValueError("API key is required. Please set your Riot API key.")
        
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://{region}.api.riotgames.com"
        self.headers = {"X-Riot-Token": api_key}
        self.last_request_time = 0
        
        print(f"Initialized Riot API client for region: {region}")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make a rate-limited request to the Riot API.
        
        Args:
            endpoint (str): API endpoint
            params (dict): Query parameters
            
        Returns:
            dict: API response data or None if failed
        """
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - time_since_last)
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                self.last_request_time = time.time()
                response = requests.get(url, headers=self.headers, params=params or {})
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit exceeded
                    print("Rate limit exceeded. Waiting...")
                    time.sleep(10)  # Wait longer for rate limit reset
                    continue
                elif response.status_code == 404:
                    print(f"Resource not found: {url}")
                    return None
                else:
                    print(f"API Error {response.status_code}: {response.text}")
                    return None
                    
            except requests.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    def get_summoner_by_name(self, summoner_name: str) -> Optional[Dict]:
        """
        Get summoner information by summoner name.
        
        Args:
            summoner_name (str): The summoner name
            
        Returns:
            dict: Summoner information or None if not found
        """
        endpoint = f"/lol/summoner/v4/summoners/by-name/{summoner_name}"
        return self._make_request(endpoint)
    
    def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict]:
        """
        Get summoner information by PUUID.
        
        Args:
            puuid (str): The summoner PUUID
            
        Returns:
            dict: Summoner information or None if not found
        """
        endpoint = f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return self._make_request(endpoint)
    
    def get_match_history(self, puuid: str, count: int = 20, start: int = 0) -> Optional[List[str]]:
        """
        Get match history for a summoner.
        
        Args:
            puuid (str): The summoner PUUID
            count (int): Number of matches to retrieve (max 100)
            start (int): Starting index
            
        Returns:
            list: List of match IDs or None if failed
        """
        # Use Americas routing for match data
        americas_url = "https://americas.api.riotgames.com"
        url = f"{americas_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        
        params = {"start": start, "count": min(count, 100)}
        
        # Make request with rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - time_since_last)
        
        try:
            self.last_request_time = time.time()
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get match history: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error getting match history: {e}")
            return None
    
    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Get detailed match information.
        
        Args:
            match_id (str): The match ID
            
        Returns:
            dict: Match details or None if failed
        """
        # Use Americas routing for match data
        americas_url = "https://americas.api.riotgames.com"
        url = f"{americas_url}/lol/match/v5/matches/{match_id}"
        
        # Make request with rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - time_since_last)
        
        try:
            self.last_request_time = time.time()
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get match details: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error getting match details: {e}")
            return None
    
    def get_league_entries(self, summoner_id: str) -> Optional[List[Dict]]:
        """
        Get ranked league entries for a summoner.
        
        Args:
            summoner_id (str): The summoner ID
            
        Returns:
            list: League entries or None if failed
        """
        endpoint = f"/lol/league/v4/entries/by-summoner/{summoner_id}"
        return self._make_request(endpoint)

class DataCollector:
    """
    High-level data collection utilities for building datasets.
    """
    
    def __init__(self, api_client: RiotAPIClient):
        """
        Initialize the data collector.
        
        Args:
            api_client (RiotAPIClient): Initialized API client
        """
        self.api_client = api_client
        self.collected_data = {
            'summoners': [],
            'matches': [],
            'match_details': []
        }
    
    def collect_summoner_data(self, summoner_names: List[str]) -> pd.DataFrame:
        """
        Collect data for multiple summoners.
        
        Args:
            summoner_names (list): List of summoner names
            
        Returns:
            DataFrame: Summoner data
        """
        summoner_data = []
        
        for name in summoner_names:
            print(f"Collecting data for summoner: {name}")
            
            summoner = self.api_client.get_summoner_by_name(name)
            if summoner:
                # Get league information
                league_entries = self.api_client.get_league_entries(summoner['id'])
                
                summoner_info = {
                    'name': summoner['name'],
                    'puuid': summoner['puuid'],
                    'summoner_level': summoner['summonerLevel'],
                    'account_id': summoner['accountId'],
                    'summoner_id': summoner['id']
                }
                
                # Add rank information if available
                if league_entries:
                    for entry in league_entries:
                        queue_type = entry['queueType']
                        summoner_info[f'{queue_type}_tier'] = entry.get('tier', 'UNRANKED')
                        summoner_info[f'{queue_type}_rank'] = entry.get('rank', 'UNRANKED')
                        summoner_info[f'{queue_type}_lp'] = entry.get('leaguePoints', 0)
                        summoner_info[f'{queue_type}_wins'] = entry.get('wins', 0)
                        summoner_info[f'{queue_type}_losses'] = entry.get('losses', 0)
                
                summoner_data.append(summoner_info)
                self.collected_data['summoners'].append(summoner_info)
        
        return pd.DataFrame(summoner_data)
    
    def collect_match_data(self, puuid: str, num_matches: int = 10) -> pd.DataFrame:
        """
        Collect detailed match data for a summoner.
        
        Args:
            puuid (str): Summoner PUUID
            num_matches (int): Number of recent matches to collect
            
        Returns:
            DataFrame: Match data
        """
        match_data = []
        
        # Get match history
        match_ids = self.api_client.get_match_history(puuid, count=num_matches)
        
        if not match_ids:
            print("No match history found")
            return pd.DataFrame()
        
        print(f"Collecting data for {len(match_ids)} matches...")
        
        for match_id in match_ids:
            print(f"Processing match: {match_id}")
            
            match_details = self.api_client.get_match_details(match_id)
            if not match_details:
                continue
            
            # Extract match info
            match_info = match_details['info']
            participants = match_info['participants']
            
            # Find the target participant
            target_participant = None
            for participant in participants:
                if participant['puuid'] == puuid:
                    target_participant = participant
                    break
            
            if target_participant:
                match_record = {
                    'match_id': match_id,
                    'game_duration': match_info['gameDuration'],
                    'game_mode': match_info['gameMode'],
                    'game_type': match_info['gameType'],
                    'champion_name': target_participant['championName'],
                    'champion_id': target_participant['championId'],
                    'kills': target_participant['kills'],
                    'deaths': target_participant['deaths'],
                    'assists': target_participant['assists'],
                    'total_damage_dealt': target_participant['totalDamageDealt'],
                    'total_damage_to_champions': target_participant['totalDamageDealtToChampions'],
                    'cs': target_participant['totalMinionsKilled'] + target_participant.get('neutralMinionsKilled', 0),
                    'gold_earned': target_participant['goldEarned'],
                    'win': target_participant['win'],
                    'vision_score': target_participant['visionScore'],
                    'game_ended_in_surrender': match_info.get('gameEndedInSurrender', False),
                    'game_start_timestamp': match_info['gameStartTimestamp']
                }
                
                match_data.append(match_record)
                self.collected_data['match_details'].append(match_record)
        
        return pd.DataFrame(match_data)
    
    def export_data(self, filename: str, format: str = 'csv') -> None:
        """
        Export collected data to file.
        
        Args:
            filename (str): Output filename
            format (str): Export format ('csv' or 'json')
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == 'csv':
            # Export summoners
            if self.collected_data['summoners']:
                summoners_df = pd.DataFrame(self.collected_data['summoners'])
                summoners_df.to_csv(f"summoners_{timestamp}.csv", index=False)
                print(f"Exported summoner data to summoners_{timestamp}.csv")
            
            # Export matches
            if self.collected_data['match_details']:
                matches_df = pd.DataFrame(self.collected_data['match_details'])
                matches_df.to_csv(f"matches_{timestamp}.csv", index=False)
                print(f"Exported match data to matches_{timestamp}.csv")
        
        elif format.lower() == 'json':
            output_file = f"{filename}_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(self.collected_data, f, indent=2)
            print(f"Exported all data to {output_file}")

# Example usage and testing functions
def main():
    """
    Example usage of the Riot API data acquisition script.
    """
    # Set your API key here!
    api_key = API_KEY or input("Enter your Riot API key: ")
    
    if not api_key:
        print("Please set your API key in the API_KEY variable or when prompted.")
        return
    
    # Initialize API client
    client = RiotAPIClient(api_key, region='na1')
    collector = DataCollector(client)
    
    # Example 1: Get summoner information
    print("\n=== Example 1: Summoner Information ===")
    summoner_name = input("Enter a summoner name (or press Enter for 'Faker'): ").strip()
    if not summoner_name:
        summoner_name = "Faker"
    
    summoner_df = collector.collect_summoner_data([summoner_name])
    if not summoner_df.empty:
        print("\nSummoner Data:")
        print(summoner_df.to_string())
        
        # Example 2: Get match history for this summoner
        print(f"\n=== Example 2: Match History for {summoner_name} ===")
        puuid = summoner_df.iloc[0]['puuid']
        matches_df = collector.collect_match_data(puuid, num_matches=5)
        
        if not matches_df.empty:
            print("\nRecent Match Data:")
            print(matches_df[['champion_name', 'kills', 'deaths', 'assists', 'win']].to_string())
            
            # Calculate some basic statistics
            print(f"\nBasic Statistics:")
            print(f"Win Rate: {matches_df['win'].mean():.2%}")
            print(f"Average KDA: {(matches_df['kills'] + matches_df['assists']).mean() / matches_df['deaths'].mean():.2f}")
            print(f"Average CS: {matches_df['cs'].mean():.1f}")
    
    # Export data
    print("\n=== Exporting Data ===")
    collector.export_data("riot_data", format='csv')
    
    print("\nData collection complete!")

if __name__ == "__main__":
    main()
