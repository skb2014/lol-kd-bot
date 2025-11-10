# lol-kd-bot

A Discord bot that periodically checks a League of Legends account’s recent matches via Riot’s API and posts results to a Discord channel. Designed to run 24/7 (e.g., on a Raspberry Pi). Default polling is frequent (60s), NA platform (`na1`) with `americas` match routing.

## Features
- Polls Riot Match V5 for the latest match(s) and announces new ones only (tracks last seen in SQLite)
- Resolves PUUID automatically from `SUMMONER_NAME` if not provided
- Posts a summary (win/loss, champion, K/D/A, K/D ratio) to a specified Discord channel
- Warns when K/D is below a configured threshold
- Basic rate-limit handling and retries

## Requirements
- Python 3.9+ recommended
- A Discord bot token and a channel ID where the bot can post
- A Riot API key

## Setup
1) Create and activate a virtual environment (Windows PowerShell):
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies:
```
pip install -r requirements.txt
```

3) Configure environment variables. You can create a `.env` file in the project root (loaded automatically if present):
```
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=123456789012345678
RIOT_API_KEY=your_riot_api_key

# Target accounts (preferred)
# Provide one or more Riot IDs as comma-separated values (Name#TAG)
# Example: RIOT_IDS="PlayerOne#NA1,Another#1234"
RIOT_IDS="LittleYay#NA1,Mewzer2#NA1,voidfłight#NA1,skb#4559"

# Legacy single-target fallback (use only if not setting RIOT_IDS)
SUMMONER_NAME=YourSummonerName
# SUMMONER_PUUID=optional_if_you_know_it

# Regions
REGION=na1           # platform routing for Summoner-V4 (na1 default)
MATCH_REGION=americas  # regional routing for Match-V5 (americas default)

# Behavior
CHECK_INTERVAL=60     # seconds (min enforced at 15s)
KD_THRESHOLD=0.7
```

Notes:
- RIOT_IDS uses the global Riot ID format (Name#TAG) and will be resolved via the Account-V1 API using the regional host (MATCH_REGION).
- Special characters are supported (e.g., `ł` in `voidfłight`).
- Important: In .env files, `#` starts a comment. Wrap the entire RIOT_IDS value in quotes (e.g., `RIOT_IDS="Name#TAG,Another#1234"`) or escape each `#` as `\#`.
- If RIOT_IDS is set, SUMMONER_NAME/SUMMONER_PUUID are ignored.

4) Run the bot:
```
python main.py
```

## Raspberry Pi notes
- Ensure your Python version is supported (3.9+ recommended).
- Use a virtual environment on the Pi as well:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## How it works
- On startup, the bot validates config and initializes a small SQLite database (`state.db`).
- A background task polls Riot’s API every `CHECK_INTERVAL` seconds.
- It fetches 1–2 latest match IDs and compares to the last seen for your PUUID; only new matches are announced.
- Messages include win/loss, champion, K/D/A, and K/D ratio. If below `KD_THRESHOLD`, the message is prefixed with a warning.

## Changing regions
- For North America, keep `REGION=na1` and `MATCH_REGION=americas` (defaults).
- For other platforms, set `REGION` accordingly (e.g., `euw1`, `kr`).
- For Match V5 regional routing, use one of: `americas`, `europe`, `asia`, `sea` depending on the account region.

## Permissions
- Invite your Discord bot with permissions to send messages in the target channel.

## Troubleshooting
- Rate limits: If you see 429s, the bot auto-backs off using the `Retry-After` header.
- Missing config: The bot will raise a clear error if required settings are missing.
- Verify the channel ID is correct and the bot has access.

