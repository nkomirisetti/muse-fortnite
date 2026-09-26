# Fortnite Squad Stats

Fun stat breakdowns for a casual Fortnite squad — K/D, win rates, mode splits,
squad awards, and loving roasts. Powered by the [Tracker Network API](https://tracker.gg/developers).

## Setup

1. Get a free API key at [tracker.gg/developers](https://tracker.gg/developers)
   (free tier is plenty).
2. Copy the example env file and add your key and player names:
   ```sh
   cp .env.example .env
   # edit .env and set TRN_API_KEY and SQUAD
   ```
3. Run it:
   ```sh
   python3 squad.py
   ```

That's it — no dependencies, stdlib only. The report prints to your terminal
and is also saved to `report.md`.

You can also pass the squad inline without editing `.env`:
```sh
SQUAD=player1,player2,player3 python3 squad.py
```

## Keeping things private

- Your API key lives **only** in `.env` (or the `TRN_API_KEY` environment
  variable). `.env` is gitignored and never committed.
- Player names live **only** in `.env` (or the `SQUAD` variable) too — the repo
  itself contains no real usernames.
- `.env.example` contains placeholders only — safe to share.
- If you're running this in CI, set `TRN_API_KEY` and `SQUAD` as secret env
  vars instead of committing a `.env` file.
