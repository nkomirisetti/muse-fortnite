#!/usr/bin/env python3
"""Fortnite squad stats: pull Tracker Network stats for the squad and
generate a fun breakdown — K/D, win rates, mode splits, awards, and
loving roasts.

Setup:
    cp .env.example .env   # then add your TRN-Api-Key and player names
    python3 squad.py

The API key and player names are read from env vars (or a .env file):
TRN_API_KEY and SQUAD (comma-separated Epic display names).
Never commit .env — it is gitignored, so keys and names stay private.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_BASE = "https://public-api.tracker.gg/v2/fortnite/standard/profile/epic"
MIN_MATCHES_FOR_RATE_AWARDS = 20


def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def fetch_profile(username, api_key):
    url = f"{API_BASE}/{username}"
    req = urllib.request.Request(url, headers={"TRN-Api-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        if e.code == 401:
            raise SystemExit("401 from Tracker Network: bad or missing TRN_API_KEY.")
        if e.code == 403:
            raise SystemExit("403 from Tracker Network: key lacks permission for this endpoint.")
        if e.code == 404:
            print(f"  ! {username}: profile not found or private.", file=sys.stderr)
            return None
        if e.code == 429:
            raise SystemExit("429: rate limited by Tracker Network. Wait a minute and retry.")
        raise SystemExit(f"HTTP {e.code} for {username}: {body}")


def stat(stats, key):
    """Pull the numeric value out of a Tracker stat object."""
    s = (stats or {}).get(key) or {}
    v = s.get("value")
    return v if isinstance(v, (int, float)) else None


def parse_profile(username, data):
    """Split segments into lifetime overview + per-mode overviews."""
    segments = (data or {}).get("data", {}).get("segments", [])
    lifetime, modes = None, {}
    for seg in segments:
        if seg.get("type") != "overview":
            continue
        name = (seg.get("metadata") or {}).get("name", "")
        stats = seg.get("stats", {})
        if name == "Lifetime" or (not name and lifetime is None):
            lifetime = stats
        elif name:
            modes[name] = stats
    if lifetime is None:
        return None
    return {
        "name": username,
        "matches": stat(lifetime, "matches") or 0,
        "wins": stat(lifetime, "wins") or 0,
        "win_rate": stat(lifetime, "winRate") or 0.0,
        "kills": stat(lifetime, "kills") or 0,
        "kd": stat(lifetime, "kd") or 0.0,
        "modes": {
            m: {
                "matches": stat(s, "matches") or 0,
                "wins": stat(s, "wins") or 0,
                "win_rate": stat(s, "winRate") or 0.0,
                "kd": stat(s, "kd") or 0.0,
            }
            for m, s in modes.items()
        },
    }


def kd_roast(p):
    kd, wr, m = p["kd"], p["win_rate"], p["matches"]
    if kd >= 3:
        return f"{p['name']} is absolutely frying lobbies ({kd:.2f} K/D). Touch grass? Never heard of it."
    if kd >= 2:
        return f"{p['name']} is holding this squad together ({kd:.2f} K/D). The rest of you: say thank you."
    if kd >= 1:
        return f"{p['name']} is respectably mid ({kd:.2f} K/D). Not carrying, not throwing. The glue."
    if m >= 50 and wr < 1:
        return (f"{p['name']} has a {kd:.2f} K/D across {m:,} matches and a sub-1% win rate. "
                "Has personally funded every reboot van on the island.")
    if kd >= 0.7:
        return f"{p['name']} is contributing... emotionally ({kd:.2f} K/D)."
    return f"{p['name']} is the squad's designated loot goblin ({kd:.2f} K/D). Lands, loots, dies. A tradition."


def mode_focus(p):
    modes = {m: s for m, s in p["modes"].items() if s["matches"] > 0}
    if not modes:
        return f"{p['name']}: no per-mode data available."
    main = max(modes, key=lambda m: modes[m]["matches"])
    rated = {m: s for m, s in modes.items() if s["matches"] >= 10}
    best = max(rated, key=lambda m: rated[m]["win_rate"]) if rated else None
    line = (f"{p['name']}: lives in {main} "
            f"({modes[main]['matches']:,} matches, {modes[main]['win_rate']:.1f}% wins)")
    if best and best != main:
        line += f", but somehow wins more in {best} ({rated[best]['win_rate']:.1f}%)"
    return line + "."


def build_report(players):
    now = datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y %I:%M %p %Z")
    L = [f"# Fortnite Squad Report", f"_{now}_", ""]
    L.append("## Lifetime snapshot")
    L.append("| Player | Matches | Wins | Win% | Kills | K/D |")
    L.append("|---|---|---|---|---|---|")
    for p in sorted(players, key=lambda x: x["kd"], reverse=True):
        L.append(f"| {p['name']} | {p['matches']:,} | {p['wins']:,} | "
                 f"{p['win_rate']:.1f}% | {p['kills']:,} | {p['kd']:.2f} |")
    L += ["", "## Mode focus"]
    L += [f"- {mode_focus(p)}" for p in players]
    L += ["", "## Squad awards"]
    carry = max(players, key=lambda x: x["kd"])
    clutch = max(players, key=lambda x: x["wins"])
    grinder = max(players, key=lambda x: x["matches"])
    rated = [p for p in players if p["matches"] >= MIN_MATCHES_FOR_RATE_AWARDS] or players
    menace = max(rated, key=lambda x: x["win_rate"])
    L.append(f"- **The Carry** (highest K/D): {carry['name']} — {carry['kd']:.2f}")
    L.append(f"- **Clutch Gene** (most wins): {clutch['name']} — {clutch['wins']:,}")
    L.append(f"- **No Life** (most matches, affectionate): {grinder['name']} — {grinder['matches']:,}")
    L.append(f"- **Lobby Menace** (best win rate): {menace['name']} — {menace['win_rate']:.1f}%")
    L += ["", "## Loving roasts"]
    L += [f"- {kd_roast(p)}" for p in sorted(players, key=lambda x: x["kd"])]
    total_wins = sum(p["wins"] for p in players)
    avg_kd = sum(p["kd"] for p in players) / len(players)
    L += ["", "## Verdict",
          f"Combined {total_wins:,} dubs at a {avg_kd:.2f} average K/D. "
          "Casual? Sure. Dangerous? Occasionally. Fun? Always."]
    return "\n".join(L) + "\n"


def main():
    load_dotenv()
    api_key = os.environ.get("TRN_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        raise SystemExit("Set TRN_API_KEY first: cp .env.example .env, then edit .env.")
    squad = [s.strip() for s in os.environ.get("SQUAD", "").split(",") if s.strip()]
    if not squad:
        raise SystemExit("Set SQUAD in .env (comma-separated Epic display names), "
                         "e.g. SQUAD=player1,player2,player3")

    print(f"Pulling stats for {', '.join(squad)} ...")
    players = []
    for name in squad:
        data = fetch_profile(name, api_key)
        parsed = parse_profile(name, data) if data else None
        if parsed:
            players.append(parsed)
            print(f"  ok: {name} — {parsed['matches']:,} matches, {parsed['kd']:.2f} K/D")
    if not players:
        raise SystemExit("No player data retrieved. Check names and API key.")

    report = build_report(players)
    print("\n" + report)
    with open("report.md", "w") as f:
        f.write(report)
    print("Saved to report.md")


if __name__ == "__main__":
    main()
