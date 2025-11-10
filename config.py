import os
from typing import Optional, List

try:
    # Load environment variables from a local .env file if present
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # It's fine if python-dotenv isn't installed in some environments
    pass

# Required secrets
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
RIOT_API_KEY: str = os.getenv("RIOT_API_KEY", "")

# Required IDs
DISCORD_CHANNEL_ID: Optional[int] = None
_channel = os.getenv("DISCORD_CHANNEL_ID")
if _channel:
    try:
        DISCORD_CHANNEL_ID = int(_channel)
    except ValueError:
        DISCORD_CHANNEL_ID = None

# Multiple Riot IDs support (comma-separated Name#TAG values)
# Example: RIOT_IDS="PlayerOne#NA1,Another#1234"
_RIOT_IDS_RAW = os.getenv("RIOT_IDS", "")
RIOT_IDS: List[str] = []
if _RIOT_IDS_RAW:
    # If the entire value is wrapped in matching single or double quotes, strip them
    if (len(_RIOT_IDS_RAW) >= 2) and ((_RIOT_IDS_RAW[0] == _RIOT_IDS_RAW[-1]) and _RIOT_IDS_RAW[0] in ('"', "'")):
        _RIOT_IDS_RAW = _RIOT_IDS_RAW[1:-1]
    RIOT_IDS = [item.strip() for item in _RIOT_IDS_RAW.split(",") if item.strip()]

# Summoner identification (legacy single-target fallback)
SUMMONER_NAME: Optional[str] = os.getenv("SUMMONER_NAME")
SUMMONER_PUUID: Optional[str] = os.getenv("SUMMONER_PUUID")

# Regions
# Platform routing (for Summoner-V4): e.g., na1, euw1, kr, etc.
REGION: str = os.getenv("REGION", "na1").lower()
# Regional routing (for Match-V5): americas | europe | asia | sea
MATCH_REGION: str = os.getenv("MATCH_REGION", "americas").lower()

# Behavior
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", 60))  # seconds; default 60s for frequent polling
KD_THRESHOLD: float = float(os.getenv("KD_THRESHOLD", 0.7))


def validate_config() -> None:
    """Raise ValueError if the configuration is insufficient."""
    missing = []
    if not DISCORD_TOKEN:
        missing.append("DISCORD_TOKEN")
    if DISCORD_CHANNEL_ID is None:
        missing.append("DISCORD_CHANNEL_ID (int)")
    if not RIOT_API_KEY:
        missing.append("RIOT_API_KEY")

    # At least one targeting method must be provided
    if not (RIOT_IDS or SUMMONER_PUUID or SUMMONER_NAME):
        missing.append("RIOT_IDS or SUMMONER_PUUID or SUMMONER_NAME")

    if missing:
        raise ValueError(
            "Missing or invalid configuration: " + ", ".join(missing)
        )