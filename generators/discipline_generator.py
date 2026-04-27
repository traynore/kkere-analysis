#!/usr/bin/env python3
"""Discipline Tracker Generator — Season-wide cards & frees analysis"""
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

def pts(o):
    return 3 if o == 'Goal' else (2 if o == '2 Points' else 1)

def generate():
    data_dir = Path(__file__).parent.parent / 'data'
    scored = ['Point', 'Goal', '2 Points']

    games = []
    player_cards = defaultdict(lambda: {'yellow': 0, 'black': 0, 'red': 0, 'frees': 0, 'games_with_cards': []})

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

        k_total = sum(pts(e['Outcome']) for e in events if e['Team Name'] == 'Killinkere' and e.get('Name') in ['Shot from play', 'Scoreable free'] and e['Outcome'] in scored)
        o_total = sum(pts(e['Outcome']) for e in events if e['Team Name'] != 'Killinkere' and e.get('Name') in ['Shot from play', 'Scoreable free'] and e['Outcome'] in scored)
        result = 'W' if k_total > o_total else ('L' if k_total < o_total else 'D')

        bookings = [e for e in events if e.get('Name') == 'Bookings']
        k_bookings = [b for b in bookings if b['Team Name'] == 'Killinkere']
        o_bookings = [b for b in bookings if b['Team Name'] != 'Killinkere']

        k_yellows = len([b for b in k_bookings if b['Outcome'] == 'Yellow'])
        k_blacks = len([b for b in k_bookings if b['Outcome'] == 'Black'])
        k_reds = len([b for b in k_bookings if b['Outcome'] == 'Red'])
        o_yellows = len([b for b in o_bookings if b['Outcome'] == 'Yellow'])
        o_blacks = len([b for b in o_bookings if b['Outcome'] == 'Black'])
        o_reds = len([b for b in o_bookings if b['Outcome'] == 'Red'])

        k_frees = len([e for e in events if e['Team Name'] == 'Killinkere' and e.get('Name') == 'Free conceded'])

        # Track per-player cards
        for b in k_bookings:
            p = b.get('Player', 'Unknown')
            if p:
                card = b['Outcome'].lower()
                player_cards[p][card] += 1
                player_cards[p]['games_with_cards'].append(opp)

        # Track per-player frees
        for e in events:
            if e['Team Name'] == 'Killinkere' and e.get('Name') == 'Free conceded':
                p = e.get('Player', '')
                if p:
                    player_cards[p]['frees'] += 1

        card_details = []
        for b in k_bookings:
            time_str = b.get('Time', '')
            card_details.append({
                'player': b.get('Player', 'Unknown'),
                'card': b['Outcome'],
                'time': time_str,
                'score': f"{k_total}-{o_total}"
            })

        games.append({
            'opp': opp, 'date': meta.get('date', ''), 'date_obj': date_obj, 'result': result,
            'k_yellows': k_yellows, 'k_blacks': k_blacks, 'k_reds': k_reds,
            'o_yellows': o_yellows, 'o_blacks': o_blacks, 'o_reds': o_reds,
            'k_frees': k_frees, 'k_total': k_total, 'o_total': o_total,
            'card_details': card_details
        })

    games.sort(key=lambda g: g['date_obj'])
    total = len(games)

    # Season totals
    tk_y = sum(g['k_yellows'] for g in games)
    tk_b = sum(g['k_blacks'] for g in games)
    tk_r = sum(g['k_reds'] for g in games)
    to_y = sum(g['o_yellows'] for g in games)
    to_b = sum(g['o_blacks'] for g in games)
    to_r = sum(g['o_reds'] for g in games)
    tk_frees = sum(g['k_frees'] for g in games)
    games_with_cards = [g for g in games if g['k_yellows'] + g['k_blacks'] + g['k_reds'] > 0]

    # Player table
    player_sorted = sorted(player_cards.items(), key=lambda x: x[1]['yellow'] + x[1]['black'] * 2 + x[1]['red'] * 3 + x[1]['frees'] * 0.1, reverse=True)
    player_rows = ''
    for name, d in player_sorted:
        total_cards = d['yellow'] + d['black'] + d['red']
        if total_cards == 0 and d['frees'] == 0:
            continue
        highlight = ' style="background:rgba(231,76,60,.08)"' if d['red'] > 0 else (' style="background:rgba(243,156,18,.08)"' if d['black'] > 0 else '')
        player_rows += f'<tr{highlight}><td><strong>{name}</strong></td><td>{d["yellow"]}</td><td>{d["black"]}</td><td>{d["red"]}</td><td style="font-weight:bold">{total_cards}</td></tr>\n'

    # Game-by-game table
    game_rows = ''
    for g in games:
        rc = '#2ecc71' if g['result'] == 'W' else ('#e74c3c' if g['result'] == 'L' else '#f39c12')
        k_cards = g['k_yellows'] + g['k_blacks'] + g['k_reds']
        o_cards = g['o_yellows'] + g['o_blacks'] + g['o_reds']
        details = ''
        for cd in g['card_details']:
            emoji = '🟨' if cd['card'] == 'Yellow' else ('⬛' if cd['card'] == 'Black' else '🟥')
            details += f"{emoji} {cd['player']} ({cd['time']}) "
        game_rows += f'<tr><td>{g["date"]}</td><td>v {g["opp"]}</td><td style="color:{rc};font-weight:bold">{g["result"]}</td>'
        game_rows += f'<td>{"🟨" * g["k_yellows"]}{"⬛" * g["k_blacks"]}{"🟥" * g["k_reds"]}{" —" if k_cards == 0 else ""}</td>'
        game_rows += f'<td>{"🟨" * g["o_yellows"]}{"⬛" * g["o_blacks"]}{"🟥" * g["o_reds"]}{" —" if o_cards == 0 else ""}</td>'
        game_rows += f'<td style="font-size:.8em">{details.strip() if details.strip() else "—"}</td></tr>\n'

    # Chart data
    labels = json.dumps([f"v {g['opp']}" for g in games])
    k_cards_data = json.dumps([g['k_yellows'] + g['k_blacks'] + g['k_reds'] for g in games])
    o_cards_data = json.dumps([g['o_yellows'] + g['o_blacks'] + g['o_reds'] for g in games])
    k_frees_data = json.dumps([g['k_frees'] for g in games])
    bar_colors = json.dumps(['rgba(46,204,113,0.8)' if g['result'] == 'W' else ('rgba(231,76,60,0.8)' if g['result'] == 'L' else 'rgba(243,156,18,0.8)') for g in games])
    bar_borders = json.dumps(['rgba(39,174,96,1)' if g['result'] == 'W' else ('rgba(192,57,43,1)' if g['result'] == 'L' else 'rgba(230,126,34,1)') for g in games])

    # Card incidents list
    incidents_html = ''
    for g in games:
        for cd in g['card_details']:
            emoji = '🟨' if cd['card'] == 'Yellow' else ('⬛' if cd['card'] == 'Black' else '🟥')
            rc = '#2ecc71' if g['result'] == 'W' else ('#e74c3c' if g['result'] == 'L' else '#f39c12')
            incidents_html += f'''<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #ecf0f1">
<span style="font-size:1.5em">{emoji}</span>
<div style="flex:1"><strong>{cd['player']}</strong> — {cd['card']} Card<br><span style="color:#7f8c8d;font-size:.85em">v {g['opp']} · {g['date']} · {cd['time']}</span></div>
<span style="color:{rc};font-weight:bold;font-size:.9em">{g['result']} ({g['k_total']}-{g['o_total']})</span>
</div>\n'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Discipline Tracker — Killinkere 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#2c3e50,#e74c3c);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;padding:40px;text-align:center}}
.header h1{{font-size:2.8em;margin-bottom:8px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header p{{font-size:1.2em;opacity:.85}}
.summary-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:15px;padding:25px 35px}}
.summary-card{{border-radius:14px;padding:18px;text-align:center}}
.summary-card .val{{font-size:2em;font-weight:bold}}.summary-card .lbl{{font-size:.8em;opacity:.85;margin-top:3px}}
.sc-red{{background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff}}
.sc-yellow{{background:linear-gradient(135deg,#f39c12,#e67e22);color:#fff}}
.sc-black{{background:linear-gradient(135deg,#2c3e50,#34495e);color:#fff}}
.sc-blue{{background:linear-gradient(135deg,#2980b9,#3498db);color:#fff}}
.tabs{{display:flex;background:#34495e}}.tab{{flex:1;padding:18px;text-align:center;color:#fff;cursor:pointer;transition:.3s;font-size:1.05em;font-weight:bold}}
.tab:hover{{background:#2c3e50}}.tab.active{{background:#c0392b}}
.tab-content{{display:none;padding:35px}}.tab-content.active{{display:block}}
.chart-box{{background:#fff;border-radius:15px;padding:28px;margin:22px 0;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
.chart-title{{font-size:1.4em;color:#2c3e50;margin-bottom:18px;text-align:center;font-weight:bold}}
table.disc-table{{width:100%;border-collapse:collapse;font-size:.85em}}
.disc-table th{{background:#34495e;color:#fff;padding:10px 8px;text-align:center;white-space:nowrap;cursor:pointer}}
.disc-table th:hover{{background:#2c3e50}}.disc-table td{{padding:8px;border-bottom:1px solid #ecf0f1;text-align:center}}
.disc-table tr:hover{{background:#f0f4ff}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.9em}}
</style></head><body>
<div class="container">
<div class="header">
<h1>🟨 DISCIPLINE TRACKER</h1>
<p>Killinkere GAA — 2026 Season · {total} Games Analyzed</p>
</div>

<div class="summary-row">
<div class="summary-card sc-yellow"><div class="val">{tk_y}</div><div class="lbl">Yellows</div></div>
<div class="summary-card sc-black"><div class="val">{tk_b}</div><div class="lbl">Blacks</div></div>
<div class="summary-card sc-red"><div class="val">{tk_r}</div><div class="lbl">Reds</div></div>
<div class="summary-card sc-red"><div class="val">{len(games_with_cards)}/{total}</div><div class="lbl">Games with Cards</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('players')">👤 Players</div>
<div class="tab" onclick="showTab('incidents')">🟨 Card Incidents</div>
<div class="tab" onclick="showTab('charts')">📈 Charts</div>
<div class="tab" onclick="showTab('table')">📋 Game-by-Game</div>
</div>

<div id="players" class="tab-content active">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.5em">👤 Player Discipline Record</h2>
<div style="overflow-x:auto">
<table class="disc-table">
<thead><tr><th>Player</th><th>🟨 Yellow</th><th>⬛ Black</th><th>🟥 Red</th><th>Total Cards</th></tr></thead>
<tbody>{player_rows}</tbody>
</table>
</div>
</div>

<div id="incidents" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.5em">🟨 All Card Incidents</h2>
<div style="border:1px solid #ecf0f1;border-radius:12px;overflow:hidden">
{incidents_html if incidents_html else '<div style="padding:30px;text-align:center;color:#7f8c8d">No Killinkere cards recorded this season</div>'}
</div>
</div>

<div id="charts" class="tab-content">
<div class="chart-box"><div class="chart-title">🟨 Cards per Game — Killinkere vs Opposition</div><canvas id="cardsChart"></canvas></div>
</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.5em">📋 Game-by-Game Discipline</h2>
<div style="overflow-x:auto">
<table class="disc-table" id="discTable">
<thead><tr><th>Date</th><th>Opp</th><th>Res</th><th>Our Cards</th><th>Opp Cards</th><th>Details</th></tr></thead>
<tbody>{game_rows}</tbody>
</table>
</div>
</div>

</div>
<div class="footer">Killinkere GAA · Discipline Tracker · 2026</div>

<script>
function showTab(t){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active')}}
const L={labels};
const orange='rgba(243,156,18,0.8)',orangeB='rgba(230,126,34,1)',red='rgba(231,76,60,0.8)',redB='rgba(192,57,43,1)',blue='rgba(52,152,219,0.8)',blueB='rgba(41,128,185,1)';
new Chart(document.getElementById('cardsChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Killinkere Cards',data:{k_cards_data},backgroundColor:orange,borderColor:orangeB,borderWidth:2}},{{label:'Opposition Cards',data:{o_cards_data},backgroundColor:red,borderColor:redB,borderWidth:2}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}},plugins:{{legend:{{display:true,position:'top'}}}}}}}});
document.querySelectorAll('.disc-table th').forEach((th,i)=>{{let asc=true;th.addEventListener('click',()=>{{const tbody=th.closest('table').querySelector('tbody');const rows=Array.from(tbody.querySelectorAll('tr'));rows.sort((a,b)=>{{let av=a.children[i].textContent.replace(/[🟨⬛🟥—]/g,'').trim();let bv=b.children[i].textContent.replace(/[🟨⬛🟥—]/g,'').trim();if(!isNaN(parseFloat(av))&&!isNaN(parseFloat(bv)))return asc?av-bv:bv-av;return asc?av.localeCompare(bv):bv.localeCompare(av)}});rows.forEach(r=>tbody.appendChild(r));asc=!asc}});}});
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body></html>'''

    output = Path(__file__).parent.parent / 'analysis' / 'discipline.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Generated: {output}")

if __name__ == '__main__':
    generate()
