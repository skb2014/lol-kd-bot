import asyncio
import json
import logging
import os
import sqlite3
import time
from contextlib import closing
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
import discord
from discord.ext import commands

import config

# -------------------- Logging --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("lol-kd-bot")

# -------------------- Config --------------------
config.validate_config()
DISCORD_TOKEN = config.DISCORD_TOKEN
DISCORD_CHANNEL_ID = config.DISCORD_CHANNEL_ID  # validated not None
RIOT_API_KEY = config.RIOT_API_KEY
REGION = config.REGION  # e.g., na1
MATCH_REGION = config.MATCH_REGION  # e.g., americas
SUMMONER_NAME = config.SUMMONER_NAME
SUMMONER_PUUID = config.SUMMONER_PUUID
RIOT_IDS = getattr(config, "RIOT_IDS", [])
CHECK_INTERVAL = max(15, int(config.CHECK_INTERVAL))  # be gentle: minimum 15s
KD_THRESHOLD = float(config.KD_THRESHOLD)

# -------------------- Persistence (SQLite) --------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")


def db_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS last_seen (
                puuid TEXT PRIMARY KEY,
                last_match_id TEXT
            )
            """
        )
        conn.commit()


def get_last_seen(puuid: str) -> Optional[str]:
    with db_connect() as conn:
        cur = conn.execute("SELECT last_match_id FROM last_seen WHERE puuid = ?", (puuid,))
        row = cur.fetchone()
        return row[0] if row else None


def set_last_seen(puuid: str, match_id: str) -> None:
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO last_seen (puuid, last_match_id) VALUES (?, ?)\n             ON CONFLICT(puuid) DO UPDATE SET last_match_id = excluded.last_match_id",
            (puuid, match_id),
        )
        conn.commit()

# -------------------- Riot API --------------------
SESSION = requests.Session()
SESSION.headers.update({"X-Riot-Token": RIOT_API_KEY, "User-Agent": "lol-kd-bot/1.0"})


class RiotError(Exception):
    pass


def _request_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    backoff = 1.0
    for attempt in range(5):
        resp = SESSION.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            retry = float(resp.headers.get("Retry-After", backoff))
            log.warning("Rate limited by Riot. Sleeping for %.1fs", retry)
            time.sleep(retry)
            backoff = min(backoff * 2, 60)
            continue
        if 200 <= resp.status_code < 300:
            try:
                return resp.json()
            except Exception as e:
                raise RiotError(f"Invalid JSON from Riot: {e}")
        # Retry on transient server errors
        if resp.status_code >= 500:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        # Client errors
        raise RiotError(f"Riot API error {resp.status_code}: {resp.text[:200]}")
    raise RiotError("Riot API: exhausted retries")


def get_puuid_from_name(region: str, summoner_name: str) -> Optional[str]:
    url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{quote(summoner_name)}"
    data = _request_json(url)
    return data.get("puuid") if isinstance(data, dict) else None


def get_puuid_from_riot_id(match_region: str, game_name: str, tag_line: str) -> Optional[str]:
    # Account-V1 by-riot-id requires regional routing (americas/europe/asia/sea)
    url = (
        f"https://{match_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
        f"{quote(game_name)}/{quote(tag_line)}"
    )
    data = _request_json(url)
    return data.get("puuid") if isinstance(data, dict) else None


def get_latest_match_ids(puuid: str, count: int = 1) -> List[str]:
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": max(1, min(count, 5))}
    data = _request_json(url, params=params)
    return list(data) if isinstance(data, list) else []


def get_match_details(match_id: str) -> Dict[str, Any]:
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    data = _request_json(url)
    return data if isinstance(data, dict) else {}


def calculate_kd(kills: int, deaths: int) -> float:
    return (kills / deaths) if deaths > 0 else float(kills)


# -------------------- Discord bot --------------------
intents = discord.Intents.default()
# No need for message content to just send messages
bot = commands.Bot(command_prefix="!", intents=intents)


async def ensure_puuid() -> str:
    global SUMMONER_PUUID
    if SUMMONER_PUUID:
        return SUMMONER_PUUID
    if not SUMMONER_NAME:
        raise ValueError("SUMMONER_NAME or SUMMONER_PUUID must be provided")
    loop = asyncio.get_running_loop()
    puuid = await loop.run_in_executor(None, get_puuid_from_name, REGION, SUMMONER_NAME)
    if not puuid:
        raise ValueError("Could not resolve PUUID from summoner name")
    SUMMONER_PUUID = puuid
    return puuid


async def poll_and_announce(channel: discord.abc.Messageable, puuid: str, label: str) -> None:
    last_seen = get_last_seen(puuid)

    # Fetch latest 1 or 2 to catch up
    loop = asyncio.get_running_loop()
    match_ids = await loop.run_in_executor(None, get_latest_match_ids, puuid, 2)

    if not match_ids:
        log.info("No matches found for PUUID %s", puuid)
        return

    # Determine which are new
    new_ids: List[str] = []
    for mid in match_ids:
        if mid == last_seen:
            break
        new_ids.append(mid)

    if not new_ids and (last_seen != match_ids[0]):
        # First run or DB empty: treat latest as last seen without announcing to avoid spam
        set_last_seen(puuid, match_ids[0])
        log.info("Initialized last_seen for %s to %s", label, match_ids[0])
        return

    # Announce from oldest to newest
    for mid in reversed(new_ids):
        details = await loop.run_in_executor(None, get_match_details, mid)
        try:
            info = details.get("info", {})
            participants = info.get("participants", [])
            p = next((x for x in participants if x.get("puuid") == puuid), None)
            if not p:
                continue
            kills = int(p.get("kills", 0))
            deaths = int(p.get("deaths", 0))
            assists = int(p.get("assists", 0))
            champ = p.get("championName", "?")
            win = bool(p.get("win", False))
            mode = info.get("gameMode") or info.get("queueId")
            kd = calculate_kd(kills, deaths)
            emoji = "✅" if win else "❌"
            warn = kd < KD_THRESHOLD
            prefix = "⚠️ " if warn else ""
            title = f"{prefix}{emoji} {label} on {champ} — KD {kills}/{deaths}/{assists} (K/D {kd:.2f})"
            extra = "\nNote: K/D below configured threshold" if warn else ""
            body = f"Match: `{mid}`\nMode: `{mode}`{extra}"
            await channel.send(f"{title}\n{body}")
        finally:
            set_last_seen(puuid, mid)


def parse_riot_id(riot_id: str) -> Optional[Tuple[str, str]]:
    if "#" not in riot_id:
        return None
    game, tag = riot_id.split("#", 1)
    game = game.strip()
    tag = tag.strip()
    if not game or not tag:
        return None
    return game, tag


async def build_targets() -> List[Tuple[str, str]]:
    """Resolve configured targets to (puuid, label) tuples.
    - If RIOT_IDS present: resolve each via Account-V1 by-riot-id using MATCH_REGION.
    - Else fallback to single SUMMONER_NAME/SUMMONER_PUUID.
    """
    targets: List[Tuple[str, str]] = []
    loop = asyncio.get_running_loop()

    if RIOT_IDS:
        for rid in RIOT_IDS:
            parsed = parse_riot_id(rid)
            if not parsed:
                log.warning("Invalid RIOT_ID entry (expected Name#TAG): %s", rid)
                continue
            game_name, tag_line = parsed
            puuid = await loop.run_in_executor(None, get_puuid_from_riot_id, MATCH_REGION, game_name, tag_line)
            if not puuid:
                log.warning("Could not resolve PUUID for %s#%s", game_name, tag_line)
                continue
            label = f"{game_name}#{tag_line}"
            targets.append((puuid, label))
    else:
        # Legacy single-target mode
        puuid = await ensure_puuid()
        label = SUMMONER_NAME or puuid
        targets.append((puuid, label))

    return targets


async def monitor_loop():
    await bot.wait_until_ready()
    assert DISCORD_CHANNEL_ID is not None
    try:
        channel = await bot.fetch_channel(DISCORD_CHANNEL_ID)
    except Exception:
        log.exception("Failed to fetch channel %s", DISCORD_CHANNEL_ID)
        return

    log.info("Starting monitor loop with interval=%ss (region=%s, match_region=%s)", CHECK_INTERVAL, REGION, MATCH_REGION)

    # Resolve targets once on startup; could be refreshed periodically if desired
    try:
        targets = await build_targets()
    except Exception:
        log.exception("Failed to build targets")
        return

    if not targets:
        log.error("No valid targets to monitor. Check RIOT_IDS or SUMMONER config.")
        return

    while not bot.is_closed():
        try:
            for puuid, label in targets:
                try:
                    await poll_and_announce(channel, puuid, label)
                except Exception:
                    log.exception("Error while polling %s", label)
                # brief spacing between players to be polite
                await asyncio.sleep(1)
        except Exception:
            log.exception("Error during monitor loop iteration")
        await asyncio.sleep(CHECK_INTERVAL)


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)
    bot.loop.create_task(monitor_loop())


def main() -> None:
    init_db()
    log.info("Starting Discord bot...")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()


