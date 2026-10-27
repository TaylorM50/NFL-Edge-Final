# NFL Edge

A static NFL analytics dashboard designed for Netlify + GitHub Pages-style hosting. It loads real season data from public nflverse releases, renders all 32 team logos, ranks players, compares team efficiency, and provides a transparent baseline matchup prediction model.

## What it does
- Team rankings: points per game, yards per game, EPA/play, success rate, turnovers, and record.
- Player leaderboard: passing/rushing/receiving production and PPR fantasy points when included in the source.
- Game predictions: projected score and win probability based on scoring margin, EPA/play, and home field.
- Team logos: ESPN's public team-logo CDN.
- Scheduled data refresh: GitHub Actions runs every six hours and can be run manually.

## Important accuracy notes
- **This is not second-by-second live play-by-play.** It refreshes every six hours, but the public upstream datasets update on their own schedule. A completed play or injury will not necessarily appear immediately.
- EPA and success rate are calculated from play-by-play where the feed supports them.
- Risk-worthy throws are not an official universal NFL statistic. The site does not invent an accuracy grade when no trusted charting source is available.
- Pressure rate needs reliable pressure charting. If the source does not contain it, the site shows it as unavailable instead of treating sacks as pressure.
- The prediction model is a transparent baseline, not a professional betting model. It does not yet include injury status, weather, player-level matchup grades, odds, rest, or travel.
- This project uses public nflverse data; attribution: nflverse (CC BY 4.0 for most datasets, subject to each dataset's specific license). Review current terms before redistributing at scale.

## Publish it
1. Upload these files and folders to your GitHub repository, keeping the folder structure.
2. In GitHub, open **Actions** → **Update NFL Edge data** → **Run workflow**.
3. Wait for the run to finish. Confirm `data/data.json` exists and is committed.
4. In Netlify, ensure the site is connected to the same repository. Set **Build command** to blank / none and **Publish directory** to `.` (the repository root), then trigger a deploy.
5. Open the deployed site. The header should say “Real data loaded” and the team/player tables should have rows.
6. To confirm future updates, open the workflow run and inspect its log. The bot commits refreshed `data/data.json` when data changes.

## If the workflow fails
Open the failed job log. The public release URL layout or available season file may have changed. The script tries the configured season and previous season for the team/player weekly files, but play-by-play is currently configured for the same candidate years only through the team/player list logic; check the log and update the upstream URL if nflverse changes release names.

## Folder structure
- `index.html` — dashboard layout
- `styles.css` — visual styling
- `app.js` — rendering, sorting, searching, predictions
- `scripts/update_data.py` — data ingestion and metrics aggregation
- `.github/workflows/update-data.yml` — scheduled refresh
- `data/data.json` — generated automatically by workflow; should not be hand-edited
