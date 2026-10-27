const DATA_URL = "data/data.json";
let DATA = null;
const $ = (id) => document.getElementById(id);
const num = (v, digits=1) => Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : "—";
const int = (v) => Number.isFinite(Number(v)) ? Math.round(Number(v)).toLocaleString() : "—";
const signed = (v,d=2) => Number.isFinite(Number(v)) ? `${Number(v)>0?"+":""}${Number(v).toFixed(d)}` : "—";
const logo = (abbr) => `https://a.espncdn.com/i/teamlogos/nfl/500/${String(abbr||"").toLowerCase()}.png`;
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function metric(v, digits=1){return v===null||v===undefined||!Number.isFinite(Number(v))?"—":num(v,digits)}
async function loadData(){
  $("data-status").textContent="Refreshing data…";
  try{
    const res=await fetch(`${DATA_URL}?t=${Date.now()}`,{cache:"no-store"});
    if(!res.ok) throw new Error(`Data file unavailable (${res.status})`);
    const data=await res.json();
    if(!Array.isArray(data.teams)||!data.teams.length) throw new Error("Data package has no team metrics");
    DATA=data; renderAll();
    $("data-status").textContent=data.meta?.mode==="live"?"Real data loaded":"Data package loaded";
    $("updated-at").textContent=data.meta?.updated_at?new Date(data.meta.updated_at).toLocaleString([], {month:"short",day:"numeric",hour:"numeric",minute:"2-digit"}):"—";
    $("season-label").textContent=`${data.meta?.season||"NFL"} Season`;
  }catch(e){
    $("data-status").textContent="Data feed unavailable";
    $("teams-body").innerHTML=`<tr><td colspan="8" class="empty">Could not load ${esc(DATA_URL)}. Run the GitHub Actions workflow and confirm data/data.json was committed. Details: ${esc(e.message)}</td></tr>`;
    $("players-body").innerHTML=`<tr><td colspan="9" class="empty">Player metrics are unavailable until the data workflow succeeds.</td></tr>`;
    $("top-offense").textContent="—";
  }
}
function renderAll(){
 const teams=DATA.teams||[], players=DATA.players||[], games=DATA.games||[];
 $("teams-count").textContent=teams.length;
 $("games-count").textContent=games.length;
 const best=[...teams].filter(t=>Number.isFinite(t.points_per_game)).sort((a,b)=>b.points_per_game-a.points_per_game)[0];
 $("top-offense").textContent=best?.abbr||"—";
 renderTeams();renderPlayers();populateTeamSelects();renderGames();
}
function renderTeams(){
 const q=$("team-search").value.toLowerCase(), sort=$("team-sort").value;
 const key={points:"points_per_game",epa:"epa_per_play",yards:"yards_per_game",success:"success_rate",turnovers:"turnovers"}[sort];
 let teams=(DATA.teams||[]).filter(t=>`${t.name} ${t.abbr}`.toLowerCase().includes(q));
 teams.sort((a,b)=>{let x=a[key],y=b[key]; if(x==null)return 1;if(y==null)return -1;return sort==="turnovers"?x-y:y-x;});
 $("teams-body").innerHTML=teams.map((t,i)=>`<tr><td class="rank">${i+1}</td><td><div class="team-cell"><img class="team-logo" loading="lazy" src="${logo(t.abbr)}" alt="" onerror="this.style.visibility='hidden'"><span>${esc(t.name)} <small style="color:var(--muted)">${esc(t.abbr)}</small></span></div></td><td>${t.wins??"—"}-${t.losses??"—"}${t.ties?`-${t.ties}`:""}</td><td>${metric(t.points_per_game)}</td><td>${metric(t.yards_per_game)}</td><td class="${Number(t.epa_per_play)>0?'positive':Number(t.epa_per_play)<0?'negative':''}">${metric(t.epa_per_play,3)}</td><td>${t.success_rate==null?"—":`${metric(t.success_rate*100)}%`}</td><td>${t.turnovers??"—"}</td></tr>`).join("")||`<tr><td colspan="8" class="empty">No teams match that search.</td></tr>`;
}
const playerKeys={pass_yards:"pass_yards",pass_tds:"pass_tds",rush_yards:"rush_yards",rec_yards:"rec_yards",rec_tds:"rec_tds",fantasy_points:"fantasy_points"};
function renderPlayers(){
 const q=$("player-search").value.toLowerCase(), key=playerKeys[$("player-sort").value]||"pass_yards";
 const labels={pass_yards:"PASS YDS",pass_tds:"PASS TD",rush_yards:"RUSH YDS",rec_yards:"REC YDS",rec_tds:"REC TD",fantasy_points:"FANTASY PTS"};
 $("player-metric-heading").textContent=labels[key]||"STAT";
 let players=(DATA.players||[]).filter(p=>`${p.name} ${p.team} ${p.position}`.toLowerCase().includes(q)&&p[key]!=null);
 players.sort((a,b)=>(Number(b[key])||0)-(Number(a[key])||0));
 $("players-body").innerHTML=players.slice(0,150).map((p,i)=>`<tr><td class="rank">${i+1}</td><td><div class="player-cell"><span class="player-avatar">${esc((p.name||"?").split(" ").map(x=>x[0]).slice(0,2).join(""))}</span>${esc(p.name)}</div></td><td><div class="team-cell"><img class="team-logo" loading="lazy" src="${logo(p.team)}" alt="" onerror="this.style.visibility='hidden'">${esc(p.team||"—")}</div></td><td>${esc(p.position||"—")}</td><td>${p.games??"—"}</td><td class="positive">${int(p[key])}</td><td>${int(p.pass_tds)}</td><td>${int(p.rush_yards)}</td><td>${int(p.rec_yards)}</td></tr>`).join("")||`<tr><td colspan="9" class="empty">No player rows available for this category/search. Check the update workflow.</td></tr>`;
}
function populateTeamSelects(){
 const teams=[...(DATA.teams||[])].sort((a,b)=>a.name.localeCompare(b.name));
 const options=teams.map(t=>`<option value="${esc(t.abbr)}">${esc(t.name)} (${esc(t.abbr)})</option>`).join("");
 const h=$("home-team"),a=$("away-team"),oldH=h.value,oldA=a.value;
 h.innerHTML=options;a.innerHTML=options;
 h.value=teams.some(t=>t.abbr===oldH)?oldH:(teams.find(t=>t.abbr==="KC")?.abbr||teams[0]?.abbr);
 a.value=teams.some(t=>t.abbr===oldA)?oldA:(teams.find(t=>t.abbr==="BUF")?.abbr||teams[1]?.abbr);
}
function renderGames(){
 const games=(DATA.games||[]).slice(0,9);
 $("recent-games").innerHTML=games.map(g=>`<article class="game"><div class="game-head"><span>${esc(g.week_label||"Completed game")}</span><span>${esc(g.date||"")}</span></div><div class="game-team"><span><img src="${logo(g.away)}" onerror="this.style.visibility='hidden'">${esc(g.away)}</span><b>${g.away_score??"—"}</b></div><div class="game-team"><span><img src="${logo(g.home)}" onerror="this.style.visibility='hidden'">${esc(g.home)}</span><b>${g.home_score??"—"}</b></div><div class="game-head"><span>${esc(g.winner||"Final")}</span><span>${g.margin==null?"":`${Math.abs(g.margin)} pt margin`}</span></div></article>`).join("")||`<p class="empty">No completed game results in the current feed.</p>`;
}
function predict(){
 const home=(DATA.teams||[]).find(t=>t.abbr===$("home-team").value),away=(DATA.teams||[]).find(t=>t.abbr===$("away-team").value);
 if(!home||!away)return;
 if(home.abbr===away.abbr){$("prediction-result").innerHTML='<div class="empty">Choose two different teams to compare a matchup.</div>';return;}
 const n=v=>Number.isFinite(Number(v))?Number(v):0;
 // Score margin is season scoring differential per game; EPA is a smaller supporting signal.
 const homeMargin=n(home.points_per_game)-n(home.points_allowed_per_game);
 const awayMargin=n(away.points_per_game)-n(away.points_allowed_per_game);
 const homeEPA=n(home.epa_per_play), awayEPA=n(away.epa_per_play);
 const delta=(homeMargin-awayMargin)*0.105+(homeEPA-awayEPA)*4.2+2.0; // home-field adjustment
 const homeProb=1/(1+Math.exp(-delta/5.7));
 const homeScore=Math.max(0,Math.round((n(home.points_per_game)+n(away.points_allowed_per_game)+2.2)/2));
 const awayScore=Math.max(0,Math.round((n(away.points_per_game)+n(home.points_allowed_per_game)-2.2)/2));
 const winner=homeProb>=.5?home:away, winProb=Math.max(homeProb,1-homeProb);
 const edges=[
  {title:"Scoring margin",text:`${home.abbr}: ${signed(homeMargin,1)} pts/game · ${away.abbr}: ${signed(awayMargin,1)} pts/game`,val:homeMargin-awayMargin},
  {title:"EPA per play",text:`${home.abbr}: ${signed(homeEPA,3)} · ${away.abbr}: ${signed(awayEPA,3)}`,val:homeEPA-awayEPA},
  {title:"Defense",text:`Points allowed: ${home.abbr} ${metric(home.points_allowed_per_game)} / ${away.abbr} ${metric(away.points_allowed_per_game)} per game`,val:n(away.points_allowed_per_game)-n(home.points_allowed_per_game)}
 ];
 const verdict=winProb<.56?"Very close matchup":winProb<.66?"Lean, not a lock":"Clearer model edge";
 $("prediction-result").innerHTML=`<div class="prediction-card"><div class="prediction-title"><h3>${esc(home.name)} vs. ${esc(away.name)}</h3><span class="eyebrow">${verdict.toUpperCase()}</span></div><p style="color:var(--muted);margin:8px 0 0">Model pick: <b style="color:var(--green)">${esc(winner.name)}</b> · ${(winProb*100).toFixed(1)}% estimated win probability</p><div class="prob-row"><div class="prob"><span style="color:var(--muted)">${esc(home.abbr)} · HOME</span><strong>${(homeProb*100).toFixed(1)}%</strong><div class="bar"><span style="width:${homeProb*100}%"></span></div><p>Projected points: <b>${homeScore}</b></p></div><div class="prob"><span style="color:var(--muted)">${esc(away.abbr)} · AWAY</span><strong>${((1-homeProb)*100).toFixed(1)}%</strong><div class="bar"><span style="width:${(1-homeProb)*100}%"></span></div><p>Projected points: <b>${awayScore}</b></p></div></div><div class="edge-list">${edges.map(e=>`<div class="edge"><b>${e.title} ${Math.abs(e.val)<.05?"· Even":e.val>0?`· ${home.abbr} edge`:`· ${away.abbr} edge`}</b>${esc(e.text)}</div>`).join("")}</div><p class="source-note">Estimate based on available season data and a small home-field advantage. Injury status, weather, rest, travel, starting QB certainty, and matchup-specific player availability are not included unless provided in the data feed.</p></div>`;
}
document.querySelectorAll(".tab").forEach(btn=>btn.addEventListener("click",()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===btn));document.querySelectorAll(".panel").forEach(p=>p.classList.toggle("active",p.id===`panel-${btn.dataset.tab}`));}));
$("team-search").addEventListener("input",renderTeams);$("team-sort").addEventListener("change",renderTeams);$("player-search").addEventListener("input",renderPlayers);$("player-sort").addEventListener("change",renderPlayers);$("predict-btn").addEventListener("click",predict);$("refresh-btn").addEventListener("click",loadData);
loadData();
// Re-fetch the published data package periodically; actual upstream freshness depends on the workflow schedule.
setInterval(loadData,5*60*1000);
