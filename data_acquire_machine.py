import requests, pandas as pd, time
from collections import deque
API_KEY = "RGAPI-453a07db-befb-4026-ad3d-aa9a0120f3ce"
REGION = "na1"
ROUTING = "americas"
QUEUE_SOLODUO = 420
RATE_LIMIT_DELAY = 1.2
class RiotAPIClient:
    def __init__(self, api_key, region="na1", routing="americas"):
        self.api_key = api_key
        self.region = region
        self.routing = routing
        self.headers = {"X-Riot-Token": self.api_key}
        self.request_times = deque()

    def _get(self, url, params=None):
        while True:  # keep retrying until success or fatal error
            # enforce local rate limit ~95 requests / 2 minutes
            while len(self.request_times) >= 95:
                if time.time() - self.request_times[0] > 120:
                    self.request_times.popleft()
                else:
                    time.sleep(1)

            try:
                r = requests.get(url, headers=self.headers, params=params)
            except Exception as e:
                print(f"⚠️ Network error: {e}, retrying in 10s...")
                time.sleep(10)
                continue

            if r.status_code == 200:
                self.request_times.append(time.time())
                return r.json()

            elif r.status_code == 429:
                # too many requests – Riot sends a Retry-After header
                retry_after = int(r.headers.get("Retry-After", 10))
                print(f"⏳ Rate limit hit. Waiting {retry_after} seconds...")
                time.sleep(retry_after + 1)
                continue  # retry

            elif r.status_code in [500, 502, 503, 504]:
                # server-side error, retry after short wait
                print(f"⚠️ Server error {r.status_code}, retrying in 5s...")
                time.sleep(5)
                continue

            else:
                # fatal (e.g., 403 bad key, 404 not found)
                print(f"❌ Request failed: {url}")
                print(f"Status {r.status_code}: {r.text}")
                return None

    def get_challenger_solo(self):
        url = f"https://{self.region}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
        return self._get(url)

    def get_match_history(self, puuid, count=5):
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count, "queue": QUEUE_SOLODUO}
        return self._get(url, params=params)

    # 👇 new methods
    def get_match_details(self, match_id):
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self._get(url)

    def get_match_timeline(self, match_id):
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
        return self._get(url)
def extract_collapsed_snapshots(match_details, match_timeline, minutes=[10, 15, 20, 25]):
    rows = []
    info = match_details.get("info", {})
    meta = match_details.get("metadata", {})
    if not info or "teams" not in info or not match_timeline:
        return rows

    match_id = meta.get("matchId", "")
    patch = info.get("gameVersion")
    queue_id = info.get("queueId")
    if queue_id != QUEUE_SOLODUO:
        return rows

    participants = info["participants"]
    frames = match_timeline.get("info", {}).get("frames", [])
    if not frames:
        return rows

    team100 = next(team for team in info["teams"] if team["teamId"] == 100)
    final_win = int(team100.get("win", False))

    max_min = len(frames) - 1
    for minute in minutes:
        if minute > max_min:
            continue
        frame = frames[minute]

        team_stats = {}
        for team in info["teams"]:
            tid = team["teamId"]
            team_players = [p for p in participants if p["teamId"] == tid]

            gold = sum(frame["participantFrames"][str(p["participantId"])]["totalGold"]
                       for p in team_players)
            xp = sum(frame["participantFrames"][str(p["participantId"])]["xp"]
                     for p in team_players)
            cs = sum(frame["participantFrames"][str(p["participantId"])]["minionsKilled"] +
                     frame["participantFrames"][str(p["participantId"])]["jungleMinionsKilled"]
                     for p in team_players)

            towers = sum(1 for e in frame.get("events", [])
                         if e["type"] == "BUILDING_KILL" and e.get("buildingType") == "TOWER_BUILDING"
                         and e["killerId"] in [p["participantId"] for p in team_players])
            dragons = sum(1 for e in frame.get("events", [])
                          if e["type"] == "ELITE_MONSTER_KILL" and e.get("monsterType") == "DRAGON"
                          and e["killerId"] in [p["participantId"] for p in team_players])

            team_stats[tid] = {"gold": gold, "xp": xp, "cs": cs,
                               "towers": towers, "dragons": dragons}

        if 100 in team_stats and 200 in team_stats:
            row = {
                "match_id": match_id,
                "patch": patch,
                "minute": minute,
                "gold_diff": team_stats[100]["gold"] - team_stats[200]["gold"],
                "xp_diff": team_stats[100]["xp"] - team_stats[200]["xp"],
                "cs_diff": team_stats[100]["cs"] - team_stats[200]["cs"],
                "tower_diff": team_stats[100]["towers"] - team_stats[200]["towers"],
                "dragon_diff": team_stats[100]["dragons"] - team_stats[200]["dragons"],
                "final_win": final_win,
            }
            rows.append(row)

    return rows
def extract_metadata(match_details):
    info = match_details.get("info", {})
    meta = match_details.get("metadata", {})
    if not info or "teams" not in info:
        return []

    match_id = meta.get("matchId", "")
    patch = info.get("gameVersion")
    participants = info.get("participants", [])

    # teams
    teams = {team["teamId"]: team for team in info["teams"]}
    winning_team = next((team for team in info["teams"] if team.get("win")), None)
    if not winning_team:
        return []  # safeguard

    tid_win = winning_team["teamId"]
    tid_lose = 100 if tid_win == 200 else 200
    losing_team = teams[tid_lose]

    # --- best damage dealer (winning team only) ---
    team_players = [p for p in participants if p["teamId"] == tid_win]
    best_p = max(team_players, key=lambda p: p["totalDamageDealtToChampions"])
    best_champ = best_p["championName"]
    best_lane = best_p.get("teamPosition", "UNKNOWN")
    best_damage = best_p["totalDamageDealtToChampions"]

    # --- raw objectives ---
    win_barons = winning_team["objectives"]["baron"]["kills"]
    lose_barons = losing_team["objectives"]["baron"]["kills"]
    win_dragons = winning_team["objectives"]["dragon"]["kills"]
    lose_dragons = losing_team["objectives"]["dragon"]["kills"]
    win_towers = winning_team["objectives"]["tower"]["kills"]
    lose_towers = losing_team["objectives"]["tower"]["kills"]

    row = {
        "match_id": match_id,
        "patch": patch,
        "winning_team": tid_win,
        # raw values
        # "win_barons": win_barons,
        # "win_dragons": win_dragons,
        # "win_towers": win_towers,
        # "lose_barons": lose_barons,
        # "lose_dragons": lose_dragons,
        # "lose_towers": lose_towers,
        # diffs
        "baron_diff": win_barons - lose_barons,
        "dragon_diff": win_dragons - lose_dragons,
        "tower_diff": win_towers - lose_towers,
        # best carry
        "best_champ": best_champ,
        "best_lane": best_lane,
    }
    return [row]


import json
import os

PROGRESS_FILE = "progress.txt"
SNAPS_FILE = "challenger_snapshots.csv"
META_FILE = "challenger_metadata.csv"
TARGET_MATCHES = 5000

def save_progress(new_matches, all_snaps, all_meta):
    # Append new matches to txt
    if new_matches:
        with open(PROGRESS_FILE, "a") as f:
            for mid in new_matches:
                f.write(mid + "\n")

    # Append new rows to CSVs
    if all_snaps:
        pd.DataFrame(all_snaps).to_csv(SNAPS_FILE, mode="a", header=not os.path.exists(SNAPS_FILE), index=False)
    if all_meta:
        pd.DataFrame(all_meta).to_csv(META_FILE, mode="a", header=not os.path.exists(META_FILE), index=False)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()
import random
if __name__ == "__main__":
    api = RiotAPIClient(API_KEY, region=REGION, routing=ROUTING)
    challenger = api.get_challenger_solo()
    entries = challenger["entries"]

    import random
    random.shuffle(entries)

    processed_matches = load_progress()
    all_snaps, all_meta = [], []
    match_count = len(processed_matches)

    print(f"▶️ Starting collection, already have {match_count} matches.")

    # Loop forever until we hit the target
    while match_count < TARGET_MATCHES:
        for entry in entries:
            puuid = entry.get("puuid")
            if not puuid:
                continue

            match_ids = api.get_match_history(puuid, count=20)  # bump to 20 for efficiency
            if not match_ids:
                continue

            for mid in match_ids:
                if match_count >= TARGET_MATCHES:
                    break  # ✅ only stop if we’ve hit target

                if mid in processed_matches:
                    continue

                print(f"Processing match: {mid}")
                details = api.get_match_details(mid)
                timeline = api.get_match_timeline(mid)
                if not details or not timeline:
                    continue

                all_snaps.extend(extract_collapsed_snapshots(details, timeline))
                all_meta.extend(extract_metadata(details))

                processed_matches.add(mid)
                match_count += 1

                if match_count % 5 == 0:
                    save_progress(list(processed_matches), all_snaps, all_meta)
                    all_snaps, all_meta = [], []

                print(f"✅ Collected so far: {match_count}/{TARGET_MATCHES}")

            if match_count >= TARGET_MATCHES:
                break

        # 🔄 if we finish looping all challenger players but haven’t reached target, reshuffle and keep going
        random.shuffle(entries)

    # Final save
    save_progress(list(processed_matches), all_snaps, all_meta)
    print(f"🎉 Done, collected {match_count} matches.")