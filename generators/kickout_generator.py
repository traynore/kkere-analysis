#!/usr/bin/env python3
"""Kickout Analysis Generator — Season-wide kickout retention and player breakdown"""
import csv, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def read_csv(f):
    events = []
    with open(f, 'r', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row.get('Team Name'):
                if 'Game Period' in row and 'Period' not in row: row['Period'] = row['Game Period']
                events.append(row)
    return events

def read_meta(f):
    meta = {}
    mf = Path(f).with_suffix('.meta')
    if not mf.exists():
        for c in Path(f).parent.glob('*.meta'):
            if c.stem.replace(' ', '') == Path(f).stem.replace(' ', ''):
                mf = c
                break
    if mf.exists():
        for line in open(mf):
            if '=' in line:
                k, v = line.strip().split('=', 1)
                meta[k] = v
    return meta

WON = ['Won clean', 'Short won', 'Break won']
LOST = ['Break lost', 'Lost clean', 'Short lost']

def generate():
    data_dir = Path(__file__).parent.parent / 'data'

    games = []
    player_own = defaultdict(lambda: {'won_clean': 0, 'short_won': 0, 'break_won': 0, 'total_won': 0})
    player_opp = defaultdict(lambda: {'lost_clean': 0, 'break_lost': 0, 'short_lost': 0, 'break_won': 0, 'won_clean': 0, 'total_won': 0})

    for f in sorted(data_dir.glob('Killinkere*.csv')):
        meta = read_meta(str(f))
        events = read_csv(str(f))
        teams = set(e['Team Name'] for e in events)
        if 'Killinkere' not in teams:
            continue
        opp = [t for t in teams if t != 'Killinkere'][0]

        try:
            date_obj = datetime.strptime(meta.get('date', ''), '%d/%m/%Y')
        except ValueError:
            date_obj = datetime.max

        all_ko = [e for e in events if e.get('Name') == 'Kickout' and e.get('Outcome') not in ['Sideline ball', 'Opp Kickout', 'Kickout', '']]
        own_ko = [e for e in all_ko if e['Team Name'] == 'Killinkere']
        opp_ko = [e for e in all_ko if e['Team Name'] != 'Killinkere']

        own_won = len([k for k in own_ko if k['Outcome'] in WON])
        own_lost = len([k for k in own_ko if k['Outcome'] in LOST])
        own_total = own_won + own_lost
        opp_won_by_us = len([k for k in opp_ko if k['Outcome'] in LOST])
        opp_total = len([k for k in opp_ko if k['Outcome'] in WON + LOST])

        for k in own_ko:
            p = k.get('Player', '')
            if not p or p.startswith('Player'):
                continue
            if k['Outcome'] in WON:
                player_own[p][k['Outcome'].lower().replace(' ', '_')] += 1
                player_own[p]['total_won'] += 1

        for k in opp_ko:
            p = k.get('Player', '')
            if not p or p.startswith('Player'):
                continue
            if k['Outcome'] in LOST:
                player_opp[p][k['Outcome'].lower().replace(' ', '_')] += 1
                player_opp[p]['total_won'] += 1

        scored = ['Point', 'Goal', '2 Points']
        def pts(o): return 3 if o == 'Goal' else (2 if o == '2 Points' else 1)
        k_total = sum(pts(e['Outcome']) for e in events if e['Team Name'] == 'Killinkere' and e.get('Name') in ['Shot from play', 'Scoreable free'] and e['Outcome'] in scored)
        o_total = sum(pts(e['Outcome']) for e in events if e['Team Name'] != 'Killinkere' and e.get('Name') in ['Shot from play', 'Scoreable free'] and e['Outcome'] in scored)
        result = 'W' if k_total > o_total else ('L' if k_total < o_total else 'D')

        games.append({
            'opp': opp, 'date': meta.get('date', ''), 'date_obj': date_obj, 'result': result,
            'own_won': own_won, 'own_lost': own_lost, 'own_total': own_total,
            'own_pct': round(own_won / own_total * 100) if own_total else 0,
            'opp_won_by_us': opp_won_by_us, 'opp_total': opp_total,
            'opp_pct': round(opp_won_by_us / opp_total * 100) if opp_total else 0,
        })

    games.sort(key=lambda g: g['date_obj'])
    total_games = len(games)

    season_own_won = sum(g['own_won'] for g in games)
    season_own_total = sum(g['own_total'] for g in games)
    season_own_pct = round(season_own_won / season_own_total * 100) if season_own_total else 0
    season_opp_won = sum(g['opp_won_by_us'] for g in games)
    season_opp_total = sum(g['opp_total'] for g in games)
    season_opp_pct = round(season_opp_won / season_opp_total * 100) if season_opp_total else 0

    def rec(gs):
        w = sum(1 for g in gs if g['result'] == 'W')
        d = sum(1 for g in gs if g['result'] == 'D')
        l = sum(1 for g in gs if g['result'] == 'L')
        return f'{w}W-{d}D-{l}L'

    opp_high = [g for g in games if g['opp_pct'] >= 40]
    opp_low = [g for g in games if g['opp_pct'] < 40]

    # Kickout exchange: opp KOs won minus own KOs lost
    for g in games:
        g['own_lost'] = g['own_total'] - g['own_won']
        g['ko_exchange'] = g['opp_won_by_us'] - g['own_lost']
    exchange_pos = [g for g in games if g['ko_exchange'] > 0]
    exchange_neg = [g for g in games if g['ko_exchange'] <= 0]

    # Player tables — own kickouts
    own_sorted = sorted(player_own.items(), key=lambda x: x[1]['total_won'], reverse=True)
    own_player_rows = ''
    for name, d in own_sorted:
        pct = round(d['total_won'] / season_own_won * 100, 1) if season_own_won else 0
        own_player_rows += f'<tr><td><strong>{name}</strong></td><td>{d["won_clean"]}</td><td>{d["short_won"]}</td><td>{d["break_won"]}</td><td style="font-weight:bold">{d["total_won"]}</td><td>{pct}%</td></tr>\n'

    # Player tables — opposition kickouts won
    opp_sorted = sorted(player_opp.items(), key=lambda x: x[1]['total_won'], reverse=True)
    opp_player_rows = ''
    for name, d in opp_sorted:
        opp_player_rows += f'<tr><td><strong>{name}</strong></td><td>{d["lost_clean"]}</td><td>{d["break_lost"]}</td><td>{d["short_lost"]}</td><td style="font-weight:bold">{d["total_won"]}</td></tr>\n'

    # Game table
    game_rows = ''
    for g in games:
        rc = '#2ecc71' if g['result'] == 'W' else ('#e74c3c' if g['result'] == 'L' else '#f39c12')
        own_color = '#2ecc71' if g['own_pct'] >= 70 else ('#e74c3c' if g['own_pct'] < 55 else '#f39c12')
        opp_color = '#2ecc71' if g['opp_pct'] >= 40 else '#e74c3c'
        game_rows += f'<tr><td>{g["date"]}</td><td>v {g["opp"]}</td><td style="color:{rc};font-weight:bold">{g["result"]}</td>'
        game_rows += f'<td>{g["own_won"]}/{g["own_total"]}</td><td style="color:{own_color};font-weight:bold">{g["own_pct"]}%</td>'
        game_rows += f'<td>{g["opp_won_by_us"]}/{g["opp_total"]}</td><td style="color:{opp_color};font-weight:bold">{g["opp_pct"]}%</td></tr>\n'

    # Chart data
    labels = json.dumps([f"v {g['opp']}" for g in games])
    own_pct_data = json.dumps([g['own_pct'] for g in games])
    opp_pct_data = json.dumps([g['opp_pct'] for g in games])
    bar_colors = json.dumps(['rgba(46,204,113,0.8)' if g['result'] == 'W' else ('rgba(231,76,60,0.8)' if g['result'] == 'L' else 'rgba(243,156,18,0.8)') for g in games])
    bar_borders = json.dumps(['rgba(39,174,96,1)' if g['result'] == 'W' else ('rgba(192,57,43,1)' if g['result'] == 'L' else 'rgba(230,126,34,1)') for g in games])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Kickout Analysis — Killinkere 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#1e3c72,#2a5298);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);color:#fff;padding:40px;text-align:center}}
.header h1{{font-size:2.8em;margin-bottom:8px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header p{{font-size:1.2em;opacity:.85}}
.summary-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:15px;padding:25px 35px}}
.summary-card{{border-radius:14px;padding:18px;text-align:center;color:#fff}}
.summary-card .val{{font-size:2em;font-weight:bold}}.summary-card .lbl{{font-size:.8em;opacity:.85;margin-top:3px}}
.sc-green{{background:linear-gradient(135deg,#27ae60,#2ecc71)}}
.sc-blue{{background:linear-gradient(135deg,#2980b9,#3498db)}}
.sc-purple{{background:linear-gradient(135deg,#8e44ad,#9b59b6)}}
.sc-orange{{background:linear-gradient(135deg,#e67e22,#f39c12)}}
.tabs{{display:flex;background:#34495e}}.tab{{flex:1;padding:18px;text-align:center;color:#fff;cursor:pointer;transition:.3s;font-size:1.05em;font-weight:bold}}
.tab:hover{{background:#2c3e50}}.tab.active{{background:#2a5298}}
.tab-content{{display:none;padding:35px}}.tab-content.active{{display:block}}
.pattern-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px;margin-bottom:30px}}
.pattern-card{{border-radius:14px;padding:25px}}.pattern-card h3{{font-size:1.15em;margin-bottom:12px}}
.pattern-card .insight{{font-size:.92em;color:#555;line-height:1.5;margin-bottom:14px}}
.rec{{padding:6px 14px;border-radius:8px;font-weight:bold;font-size:.9em;display:inline-block;margin:4px}}
.rec-good{{background:rgba(46,204,113,.15);color:#27ae60;border:1px solid rgba(46,204,113,.3)}}
.rec-bad{{background:rgba(231,76,60,.15);color:#c0392b;border:1px solid rgba(231,76,60,.3)}}
.pattern-green{{background:linear-gradient(135deg,rgba(46,204,113,.08),rgba(46,204,113,.15));border-left:5px solid #2ecc71}}
.pattern-blue{{background:linear-gradient(135deg,rgba(52,152,219,.08),rgba(52,152,219,.15));border-left:5px solid #3498db}}
.chart-box{{background:#fff;border-radius:15px;padding:28px;margin:22px 0;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
.chart-title{{font-size:1.4em;color:#2c3e50;margin-bottom:18px;text-align:center;font-weight:bold}}
table.ko-table{{width:100%;border-collapse:collapse;font-size:.85em}}
.ko-table th{{background:#34495e;color:#fff;padding:10px 8px;text-align:center;white-space:nowrap;cursor:pointer}}
.ko-table th:hover{{background:#2c3e50}}.ko-table td{{padding:8px;border-bottom:1px solid #ecf0f1;text-align:center}}
.ko-table tr:hover{{background:#f0f4ff}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.9em}}
</style></head><body>
<div class="container">
<div class="header">
<h1>🏐 KICKOUT ANALYSIS</h1>
<p>Killinkere GAA — 2026 Season · {total_games} Games Analyzed</p>
</div>

<div class="summary-row">
<div class="summary-card sc-green"><div class="val">{season_own_pct}%</div><div class="lbl">Own KO Retention</div></div>
<div class="summary-card sc-blue"><div class="val">{season_own_won}/{season_own_total}</div><div class="lbl">Own KOs Won</div></div>
<div class="summary-card sc-purple"><div class="val">{season_opp_pct}%</div><div class="lbl">Opp KO Won</div></div>
<div class="summary-card sc-orange"><div class="val">{season_opp_won}/{season_opp_total}</div><div class="lbl">Opp KOs Taken</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('players')">👤 Players</div>
<div class="tab" onclick="showTab('charts')">📈 Charts</div>
<div class="tab" onclick="showTab('table')">📋 Game-by-Game</div>
</div>

<div id="players" class="tab-content active">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.5em">🏐 Own Kickouts — Who Wins Them</h2>
<div style="overflow-x:auto">
<table class="ko-table">
<thead><tr><th>Player</th><th>Won Clean</th><th>Short Won</th><th>Break Won</th><th>Total</th><th>% of All</th></tr></thead>
<tbody>{own_player_rows}</tbody>
</table>
</div>

<h2 style="color:#2c3e50;text-align:center;margin:30px 0 18px;font-size:1.5em">⚔️ Opposition Kickouts — Who Wins Them For Us</h2>
<div style="overflow-x:auto">
<table class="ko-table">
<thead><tr><th>Player</th><th>Won Clean</th><th>Break Won</th><th>Short Won</th><th>Total</th></tr></thead>
<tbody>{opp_player_rows}</tbody>
</table>
</div>
</div>

<div id="charts" class="tab-content">
<div class="chart-box"><div class="chart-title">🏐 Own Kickout Retention % per Game</div><canvas id="ownChart"></canvas></div>
<div class="chart-box"><div class="chart-title">⚔️ Opposition Kickout Win % per Game</div><canvas id="oppChart"></canvas></div>
</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.5em">📋 Game-by-Game Kickouts</h2>
<div style="overflow-x:auto">
<table class="ko-table" id="koTable">
<thead><tr><th>Date</th><th>Opp</th><th>Res</th><th>Own Won</th><th>Own %</th><th>Opp Won</th><th>Opp %</th></tr></thead>
<tbody>{game_rows}</tbody>
</table>
</div>
</div>

</div>
<div class="footer">Killinkere GAA · Kickout Analysis · 2026</div>

<script>
function showTab(t){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active')}}
const L={labels};
const green='rgba(46,204,113,0.8)',greenB='rgba(39,174,96,1)',purple='rgba(155,89,182,0.8)',purpleB='rgba(142,68,173,1)';
new Chart(document.getElementById('ownChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Own KO Retention %',data:{own_pct_data},backgroundColor:{bar_colors},borderColor:{bar_borders},borderWidth:2}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}},plugins:{{legend:{{display:false}}}}}},plugins:[{{id:'t70',afterDatasetsDraw(c){{const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=c;const yp=y.getPixelForValue(70);ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='rgba(46,204,113,0.6)';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(left,yp);ctx.lineTo(right,yp);ctx.stroke();ctx.fillStyle='rgba(46,204,113,0.8)';ctx.font='bold 10px Arial';ctx.textAlign='right';ctx.fillText('70% target',right,yp-4);ctx.restore()}}}}]}});
new Chart(document.getElementById('oppChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Opp KO Win %',data:{opp_pct_data},backgroundColor:{bar_colors},borderColor:{bar_borders},borderWidth:2}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}},plugins:{{legend:{{display:false}}}}}},plugins:[{{id:'t40',afterDatasetsDraw(c){{const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=c;const yp=y.getPixelForValue(40);ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='rgba(155,89,182,0.6)';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(left,yp);ctx.lineTo(right,yp);ctx.stroke();ctx.fillStyle='rgba(155,89,182,0.8)';ctx.font='bold 10px Arial';ctx.textAlign='right';ctx.fillText('40% target',right,yp-4);ctx.restore()}}}}]}});
document.querySelectorAll('.ko-table th').forEach((th,i)=>{{let asc=true;th.addEventListener('click',()=>{{const tbody=th.closest('table').querySelector('tbody');const rows=Array.from(tbody.querySelectorAll('tr'));rows.sort((a,b)=>{{let av=a.children[i].textContent.replace('%','').trim();let bv=b.children[i].textContent.replace('%','').trim();if(!isNaN(parseFloat(av))&&!isNaN(parseFloat(bv)))return asc?av-bv:bv-av;return asc?av.localeCompare(bv):bv.localeCompare(av)}});rows.forEach(r=>tbody.appendChild(r));asc=!asc}});}});
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body></html>'''

    output = Path(__file__).parent.parent / 'analysis' / 'kickouts.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Generated: {output}")

if __name__ == '__main__':
    generate()
