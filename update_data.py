#!/usr/bin/env python3
"""Build static dashboard data from nflverse's public data releases.
Never fills missing metrics with fake values; unavailable values remain null.
"""
from __future__ import annotations
import io, json, os, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import pandas as pd

SEASON = int(os.getenv("NFL_SEASON", datetime.now(timezone.utc).year))
# During the offseason the current calendar year can be the upcoming season.
# Keep current year by default, with a fallback to prior season if current feed is not released.
BASE = "https://github.com/nflverse/nflverse-data/releases/download"
TEAMS = {
"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills",
"CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns",
"DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
"HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs",
"LA":"Los Angeles Rams","LAC":"Los Angeles Chargers","LV":"Las Vegas Raiders","MIA":"Miami Dolphins",
"MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants",
"NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SEA":"Seattle Seahawks",
"SF":"San Francisco 49ers","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"}
def get_csv(url):
    req=Request(url,headers={"User-Agent":"NFL-Edge-dashboard/1.0"})
    with urlopen(req,timeout=60) as r:
        return pd.read_csv(io.BytesIO(r.read()),low_memory=False)
def try_csv(urls):
    errors=[]
    for url in urls:
        try:
            df=get_csv(url)
            print(f"Downloaded {url} ({len(df)} rows)")
            return df
        except Exception as e:
            errors.append(f"{url}: {e}")
    raise RuntimeError("Could not download any upstream data URL:\n"+"\n".join(errors))
def col(df,*names):
    for n in names:
        if n in df.columns:return n
    return None
def numcol(df,row,*names):
    c=col(df,*names)
    if c is None:return None
    v=row.get(c)
    try:
        if pd.isna(v):return None
        return float(v)
    except (ValueError,TypeError):return None
def clean(v):
    if v is None or pd.isna(v):return None
    try:
        f=float(v)
        if not pd.notna(f):return None
        return round(f,5)
    except (ValueError,TypeError):return None
def first_valid(group, names):
    for name in names:
        if name in group.columns and group[name].notna().any():
            return name
    return None

def build():
    years=[SEASON,SEASON-1] if SEASON>2000 else [SEASON]
    team_df=try_csv([f"{BASE}/stats_team/stats_team_week_{y}.csv" for y in years])
    # Player stats package uses weekly rows and season-specific releases.
    player_df=try_csv([f"{BASE}/stats_player/stats_player_week_{y}.csv" for y in years])
    pbp=try_csv([f"{BASE}/pbp/play_by_play_{y}.csv" for y in years])
    # Use most recent season represented in the data; avoid mixing two seasons.
    season_col=col(team_df,"season")
    season=int(team_df[season_col].dropna().max()) if season_col and team_df[season_col].notna().any() else years[0]
    if season_col: team_df=team_df[team_df[season_col]==season]
    pseason=col(player_df,"season")
    if pseason: player_df=player_df[player_df[pseason]==season]
    bseason=col(pbp,"season")
    if bseason: pbp=pbp[pbp[bseason]==season]
    week_col=col(team_df,"week")
    if week_col:
        # Aggregate weekly team stats by team; count games represented by weeks/rows.
        team_df=team_df[pd.to_numeric(team_df[week_col],errors="coerce").notna()]
    teamcol=col(team_df,"team","team_abbr")
    if not teamcol: raise RuntimeError("Team stats feed lacks a team column")
    ptscol=col(team_df,"points","pts")
    ydscol=col(team_df,"total_yards","yards")
    passyds=col(team_df,"passing_yards","pass_yards")
    rushyds=col(team_df,"rushing_yards","rush_yards")
    # Compute EPA/success directly from play-by-play when fields exist.
    pbp_team=col(pbp,"posteam","offense_team")
    epa_col=col(pbp,"epa")
    playtype=col(pbp,"play_type")
    if pbp_team and epa_col:
        plays=pbp.copy()
        plays[epa_col]=pd.to_numeric(plays[epa_col],errors="coerce")
        if playtype: plays=plays[plays[playtype].isin(["pass","run"])]
        plays=plays[plays[pbp_team].isin(TEAMS)]
        epa=plays.groupby(pbp_team)[epa_col].agg(["mean","count"]).to_dict("index")
        successcol=col(plays,"success")
        success={}
        if successcol:
            plays[successcol]=pd.to_numeric(plays[successcol],errors="coerce")
            success=plays.groupby(pbp_team)[successcol].mean().to_dict()
    else:
        epa={};success={}
    # Aggregate weekly box stats using sums for season-to-date player production.
    player_id=col(player_df,"player_id","gsis_id")
    player_name=col(player_df,"player_display_name","player_name","name")
    player_team=col(player_df,"recent_team","team","team_abbr")
    player_pos=col(player_df,"position","position_group")
    if not player_name or not player_team:
        raise RuntimeError("Player stats feed is missing expected player/team fields")
    pweek=col(player_df,"week")
    if pweek: player_df=player_df[pd.to_numeric(player_df[pweek],errors="coerce").notna()]
    # Weekly player stat names in nflverse's player statistics release.
    fields={
      "pass_yards":("passing_yards","passing_yards"),
      "pass_tds":("passing_tds","passing_tds"),
      "rush_yards":("rushing_yards","rushing_yards"),
      "rec_yards":("receiving_yards","receiving_yards"),
      "rec_tds":("receiving_tds","receiving_tds"),
      "fantasy_points":("fantasy_points_ppr","fantasy_points")
    }
    pids=[player_id,player_name,player_team,player_pos]
    groupkeys=[x for x in [player_id,player_name,player_team,player_pos] if x]
    agg={}
    for key,(source,_) in fields.items():
        c=col(player_df,source)
        if c:
            player_df[c]=pd.to_numeric(player_df[c],errors="coerce")
            agg[key]=(c,"sum")
    grouped=player_df.groupby(groupkeys,dropna=False).agg(**{k:pd.NamedAgg(column=v[0],aggfunc="sum") for k,v in agg.items()}).reset_index() if agg else pd.DataFrame()
    players=[]
    if not grouped.empty:
        for _,r in grouped.iterrows():
            name=str(r[player_name]) if pd.notna(r[player_name]) else "Unknown"
            team=str(r[player_team]) if pd.notna(r[player_team]) else ""
            if team not in TEAMS: continue
            obj={"name":name,"team":team,"position":str(r[player_pos]) if player_pos and pd.notna(r[player_pos]) else None}
            if player_id: obj["player_id"]=str(r[player_id]) if pd.notna(r[player_id]) else None
            obj["games"]=None
            for k in fields:
                obj[k]=clean(r[k]) if k in grouped.columns else None
            players.append(obj)
    # Estimate games played from distinct team-game appearances when the player feed has game IDs.
    pgame=col(player_df,"game_id","old_game_id")
    if pgame and player_id:
        game_counts=player_df.groupby([player_id,player_name,player_team])[pgame].nunique().to_dict()
        for p in players:
            p["games"]=int(game_counts.get((p.get("player_id"),p["name"],p["team"]),0)) or None
    # Build team rows from weekly team totals, with W/L from play-by-play final scores.
    gameid=col(pbp,"game_id","old_game_id")
    home=col(pbp,"home_team");away=col(pbp,"away_team")
    home_score=col(pbp,"total_home_score");away_score=col(pbp,"total_away_score")
    game_rows=[]
    if gameid and home and away and home_score and away_score:
        finals=pbp.sort_values(col(pbp,"play_id") or gameid).groupby(gameid,as_index=False).tail(1)
        seen=set()
        for _,r in finals.iterrows():
            h,a=r.get(home),r.get(away)
            hs,as_=clean(r.get(home_score)),clean(r.get(away_score))
            if h not in TEAMS or a not in TEAMS or hs is None or as_ is None: continue
            # Future/in-progress games do not have a final score.
            if hs==0 and as_==0: continue
            key=str(r.get(gameid))
            if key in seen: continue
            seen.add(key)
            datecol=col(finals,"game_date","gameday")
            date=str(r.get(datecol))[:10] if datecol and pd.notna(r.get(datecol)) else ""
            w=int(hs>as_)-int(hs<as_)
            week=clean(r.get(col(finals,"week"))) if col(finals,"week") else None
            game_rows.append({"home":h,"away":a,"home_score":int(hs),"away_score":int(as_),"winner":h if w>0 else a if w<0 else "Tie","margin":int(hs-as_),"date":date,"week_label":f"Week {int(week)}" if week else "Final"})
    team_rows=[]
    for abbr,name in TEAMS.items():
        rows=team_df[team_df[teamcol]==abbr]
        if rows.empty: 
            team_rows.append({"abbr":abbr,"name":name,"wins":0,"losses":0,"ties":0,"points_per_game":None,"points_allowed_per_game":None,"yards_per_game":None,"epa_per_play":clean(epa.get(abbr,{}).get("mean")),"success_rate":clean(success.get(abbr)),"turnovers":None})
            continue
        # Filter to weeks with actual data so a future empty week cannot dilute averages.
        if ptscol: rows=rows[pd.to_numeric(rows[ptscol],errors="coerce").notna()]
        n=max(1,len(rows))
        points=float(pd.to_numeric(rows[ptscol],errors="coerce").sum()) if ptscol else None
        yards=float(pd.to_numeric(rows[ydscol],errors="coerce").sum()) if ydscol else None
        turnoverscol=col(rows,"turnovers","turnovers_lost","total_turnovers")
        turnovers=int(pd.to_numeric(rows[turnoverscol],errors="coerce").fillna(0).sum()) if turnoverscol else None
        # Record from completed game results, which is more robust than assuming all weeks played.
        w=l=t=0
        for g in game_rows:
            if g["home"]==abbr:
                w+=g["home_score"]>g["away_score"];l+=g["home_score"]<g["away_score"];t+=g["home_score"]==g["away_score"]
            elif g["away"]==abbr:
                w+=g["away_score"]>g["home_score"];l+=g["away_score"]<g["home_score"];t+=g["home_score"]==g["away_score"]
        # Defensive points allowed from game scores.
        allowed=[]
        for g in game_rows:
            if g["home"]==abbr: allowed.append(g["away_score"])
            elif g["away"]==abbr: allowed.append(g["home_score"])
        team_rows.append({
          "abbr":abbr,"name":name,"wins":int(w),"losses":int(l),"ties":int(t),
          "points_per_game":clean(points/n) if points is not None else None,
          "points_allowed_per_game":clean(sum(allowed)/len(allowed)) if allowed else None,
          "yards_per_game":clean(yards/n) if yards is not None else None,
          "epa_per_play":clean(epa.get(abbr,{}).get("mean")),
          "success_rate":clean(success.get(abbr)),
          "turnovers":turnovers
        })
    # Player rank table can use actual season stats, sorted client-side.
    players.sort(key=lambda p:(p.get("pass_yards") or p.get("rush_yards") or p.get("rec_yards") or 0),reverse=True)
    game_rows.sort(key=lambda g:(g.get("date") or ""),reverse=True)
    # keep a useful recent game sample, not thousands of results
    payload={"meta":{"mode":"live","season":season,"updated_at":datetime.now(timezone.utc).isoformat(),"source":"nflverse public data releases","team_rows":len(team_rows),"player_rows":len(players),"game_rows":len(game_rows),"notes":"Updated from the latest available upstream releases; not a second-by-second live play feed."},"teams":team_rows,"players":players,"games":game_rows[:30]}
    out=os.path.join(os.path.dirname(__file__),"..","data","data.json")
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: json.dump(payload,f,separators=(",",":"),allow_nan=False)
    print(f"Wrote {out}: {len(team_rows)} teams, {len(players)} players, {len(game_rows)} games; season={season}")
if __name__=="__main__":
    try: build()
    except Exception as e:
        print(f"DATA UPDATE FAILED: {e}",file=sys.stderr)
        sys.exit(1)
