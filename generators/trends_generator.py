#!/usr/bin/env python3
"""
Season Trends & Patterns Generator
Analyzes all match CSVs and generates an HTML trends page.
Usage: python3 trends_generator.py
"""

import csv
import json
from pathlib import Path
from datetime import datetime


def read_csv(f):
    events = []
    with open(f, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get('Team Name'):
                events.append(row)
    return events


def read_meta(f):
    meta_file = Path(f).with_suffix('.meta')
    if not meta_file.exists():
        stem = Path(f).stem
        for c in Path(f).parent.glob('*.meta'):
            if c.stem.replace(' ', '') == stem.replace(' ', ''):
                meta_file = c
                break
    meta = {}
    if meta_file.exists():
        with open(meta_file) as fh:
            for line in fh:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    meta[k] = v
    return meta


def analyze_game(csv_file):
    events = read_csv(csv_file)
    meta = read_meta(csv_file)

    teams = set(e['Team Name'] for e in events if e.get('Team Name'))
    if 'Killinkere' not in teams:
        return None
    opp = [t for t in teams if t != 'Killinkere'][0]

    all_scores = [e for e in events if e.get('Name') in ['Shot from play', 'Scoreable free']
                  and e.get('Outcome') in ['Goal', 'Point', '2 Points']]

    def pts(outcome):
        return 3 if outcome == 'Goal' else (2 if outcome == '2 Points' else 1)

    k_total = sum(pts(e['Outcome']) for e in all_scores if e['Team Name'] == 'Killinkere')
    o_total = sum(pts(e['Outcome']) for e in all_scores if e['Team Name'] != 'Killinkere')
    result = 'W' if k_total > o_total else ('L' if k_total < o_total else 'D')

    k_ht = sum(pts(e['Outcome']) for e in all_scores if e['Team Name'] == 'Killinkere' and e.get('Period') == '1')
    o_ht = sum(pts(e['Outcome']) for e in all_scores if e['Team Name'] != 'Killinkere' and e.get('Period') == '1')
    k_2h = k_total - k_ht
    o_2h = o_total - o_ht

    p2_scores = [e for e in all_scores if e.get('Period') == '2']
    first_after_ht = p2_scores[0]['Team Name'] if p2_scores else None
    first_after_ht_time = p2_scores[0].get('Time', '') if p2_scores else ''

    first_scorer = all_scores[0]['Team Name'] if all_scores else None
    last_scorer = all_scores[-1]['Team Name'] if all_scores else None

    k_run, o_run, k_best, o_best = 0, 0, 0, 0
    for e in all_scores:
        if e['Team Name'] == 'Killinkere':
            k_run += 1; o_run = 0; k_best = max(k_best, k_run)
        else:
            o_run += 1; k_run = 0; o_best = max(o_best, o_run)

    # Scoring droughts - longest gap between Killinkere scores
    k_score_times = []
    for e in all_scores:
        if e['Team Name'] == 'Killinkere' and e.get('Time'):
            t = e['Time']
            parts = t.split(':')
            if len(parts) == 3:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                k_score_times.append(secs)
    longest_drought = 0
    for i in range(1, len(k_score_times)):
        gap = k_score_times[i] - k_score_times[i - 1]
        longest_drought = max(longest_drought, gap)

    date_str = meta.get('date', '')
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        date_obj = datetime.max

    return {
        'opponent': opp,
        'date': date_str,
        'date_obj': date_obj,
        'competition': meta.get('competition', ''),
        'result': result,
        'k_total': k_total, 'o_total': o_total,
        'k_ht': k_ht, 'o_ht': o_ht,
        'k_2h': k_2h, 'o_2h': o_2h,
        'scored_first': first_scorer == 'Killinkere',
        'scored_first_after_ht': first_after_ht == 'Killinkere',
        'first_after_ht_time': first_after_ht_time,
        'scored_last': last_scorer == 'Killinkere',
        'won_2h': k_2h > o_2h,
        'drew_2h': k_2h == o_2h,
        'lost_2h': k_2h < o_2h,
        'k_best_run': k_best,
        'opp_best_run': o_best,
        'longest_drought_mins': round(longest_drought / 60, 1),
        'margin': k_total - o_total,
        'ht_lead': k_ht - o_ht,
    }


def generate():
    data_dir = Path(__file__).parent.parent / 'data'
    games = []
    for f in sorted(data_dir.glob('*.csv')):
        g = analyze_game(f)
        if g:
            games.append(g)

    games.sort(key=lambda g: g['date_obj'])

    total = len(games)
    wins = sum(1 for g in games if g['result'] == 'W')
    losses = sum(1 for g in games if g['result'] == 'L')
    draws = sum(1 for g in games if g['result'] == 'D')

    # Pattern stats
    first_ht_yes = [g for g in games if g['scored_first_after_ht']]
    first_ht_no = [g for g in games if not g['scored_first_after_ht']]
    opp_run_high = [g for g in games if g['opp_best_run'] >= 4]
    opp_run_low = [g for g in games if g['opp_best_run'] < 4]
    won_2h = [g for g in games if g['won_2h']]
    lost_2h = [g for g in games if g['lost_2h']]
    drew_2h = [g for g in games if g['drew_2h']]

    def record(gs):
        w = sum(1 for g in gs if g['result'] == 'W')
        d = sum(1 for g in gs if g['result'] == 'D')
        l = sum(1 for g in gs if g['result'] == 'L')
        return f'{w}W-{d}D-{l}L'

    # Game rows for table
    game_rows = ''
    for g in games:
        res_color = '#2ecc71' if g['result'] == 'W' else ('#e74c3c' if g['result'] == 'L' else '#f39c12')
        ht_icon = '✅' if g['scored_first_after_ht'] else '❌'
        run_color = '#e74c3c' if g['opp_best_run'] >= 4 else '#2ecc71'
        h2_icon = '✅' if g['won_2h'] else ('➖' if g['drew_2h'] else '❌')
        first_icon = '✅' if g['scored_first'] else '❌'
        last_icon = '✅' if g['scored_last'] else '❌'
        game_rows += f'''<tr>
<td>{g['date']}</td>
<td>v {g['opponent']}</td>
<td style="color:{res_color};font-weight:bold">{g['result']}</td>
<td>{g['k_total']}-{g['o_total']}</td>
<td>{g['k_ht']}-{g['o_ht']}</td>
<td>{first_icon}</td>
<td>{ht_icon}</td>
<td>{h2_icon} ({g['k_2h']}-{g['o_2h']})</td>
<td style="color:{run_color};font-weight:bold">{g['opp_best_run']}</td>
<td>{g['k_best_run']}</td>
<td>{last_icon}</td>
<td>{g['longest_drought_mins']}m</td>
</tr>
'''

    # Chart data
    chart_labels = json.dumps([f"v {g['opponent']}" for g in games])
    chart_margins = json.dumps([g['margin'] for g in games])
    chart_k_2h = json.dumps([g['k_2h'] for g in games])
    chart_o_2h = json.dumps([g['o_2h'] for g in games])
    chart_opp_runs = json.dumps([g['opp_best_run'] for g in games])
    chart_k_runs = json.dumps([g['k_best_run'] for g in games])
    chart_results = json.dumps([g['result'] for g in games])
    chart_bar_colors = json.dumps(['rgba(46,204,113,0.8)' if g['result'] == 'W' else ('rgba(231,76,60,0.8)' if g['result'] == 'L' else 'rgba(243,156,18,0.8)') for g in games])
    chart_bar_borders = json.dumps(['rgba(39,174,96,1)' if g['result'] == 'W' else ('rgba(192,57,43,1)' if g['result'] == 'L' else 'rgba(230,126,34,1)') for g in games])

    # Combo pattern: scored first after HT AND opp run < 4
    combo_yes = [g for g in games if g['scored_first_after_ht'] and g['opp_best_run'] < 4]
    combo_no = [g for g in games if not g['scored_first_after_ht'] or g['opp_best_run'] >= 4]

    # HT lead patterns
    ahead_ht = [g for g in games if g['ht_lead'] > 0]
    behind_ht = [g for g in games if g['ht_lead'] < 0]
    level_ht = [g for g in games if g['ht_lead'] == 0]

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Season Trends & Patterns — Killinkere 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);color:#fff;padding:40px;text-align:center}}
.header h1{{font-size:2.8em;margin-bottom:8px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header p{{font-size:1.2em;opacity:.85}}
.record{{display:flex;justify-content:center;gap:30px;margin-top:20px;font-size:1.3em}}
.record span{{padding:8px 20px;border-radius:20px;font-weight:bold}}
.record .w{{background:rgba(46,204,113,.3)}} .record .d{{background:rgba(243,156,18,.3)}} .record .l{{background:rgba(231,76,60,.3)}}
.tabs{{display:flex;background:#34495e}}
.tab{{flex:1;padding:18px;text-align:center;color:#fff;cursor:pointer;transition:.3s;font-size:1.05em;font-weight:bold}}
.tab:hover{{background:#2c3e50}}
.tab.active{{background:#2a5298}}
.tab-content{{display:none;padding:35px}}
.tab-content.active{{display:block}}
.pattern-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px;margin-bottom:30px}}
.pattern-card{{border-radius:14px;padding:25px;position:relative;overflow:hidden}}
.pattern-card h3{{font-size:1.15em;margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.pattern-card .insight{{font-size:.92em;color:#555;line-height:1.5;margin-bottom:14px}}
.pattern-card .record-row{{display:flex;gap:12px;margin-top:8px}}
.pattern-card .rec{{padding:6px 14px;border-radius:8px;font-weight:bold;font-size:.9em}}
.rec-good{{background:rgba(46,204,113,.15);color:#27ae60;border:1px solid rgba(46,204,113,.3)}}
.rec-bad{{background:rgba(231,76,60,.15);color:#c0392b;border:1px solid rgba(231,76,60,.3)}}
.rec-neutral{{background:rgba(243,156,18,.15);color:#e67e22;border:1px solid rgba(243,156,18,.3)}}
.pattern-green{{background:linear-gradient(135deg,rgba(46,204,113,.08),rgba(46,204,113,.15));border-left:5px solid #2ecc71}}
.pattern-red{{background:linear-gradient(135deg,rgba(231,76,60,.08),rgba(231,76,60,.15));border-left:5px solid #e74c3c}}
.pattern-blue{{background:linear-gradient(135deg,rgba(52,152,219,.08),rgba(52,152,219,.15));border-left:5px solid #3498db}}
.pattern-purple{{background:linear-gradient(135deg,rgba(155,89,182,.08),rgba(155,89,182,.15));border-left:5px solid #9b59b6}}
.pattern-gold{{background:linear-gradient(135deg,rgba(243,156,18,.08),rgba(243,156,18,.15));border-left:5px solid #f39c12}}
.chart-box{{background:#fff;border-radius:15px;padding:28px;margin:22px 0;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
.chart-title{{font-size:1.6em;color:#2c3e50;margin-bottom:18px;text-align:center;font-weight:bold}}
table.trends-table{{width:100%;border-collapse:collapse;font-size:.88em}}
.trends-table th{{background:#34495e;color:#fff;padding:11px 8px;text-align:center;white-space:nowrap;cursor:pointer}}
.trends-table th:hover{{background:#2c3e50}}
.trends-table td{{padding:9px 8px;border-bottom:1px solid #ecf0f1;text-align:center}}
.trends-table tr:hover{{background:#f0f4ff}}
.trends-table tr:nth-child(even){{background:#f8f9fa}}
.big-stat{{text-align:center;padding:20px}}
.big-stat .num{{font-size:3.5em;font-weight:bold}}
.big-stat .lbl{{font-size:1em;color:#7f8c8d;margin-top:4px}}
.summary-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:30px}}
.summary-card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:14px;padding:20px;text-align:center}}
.summary-card .val{{font-size:2em;font-weight:bold}}
.summary-card .lbl{{font-size:.82em;opacity:.85;margin-top:3px}}
.formula-box{{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;border-radius:16px;padding:30px;margin:25px 0;text-align:center}}
.formula-box h2{{font-size:1.6em;margin-bottom:15px}}
.formula-box .formula{{font-size:1.2em;opacity:.9;line-height:1.8}}
.formula-box .formula-result{{font-size:2em;font-weight:bold;margin-top:15px;color:#2ecc71}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.9em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 SEASON TRENDS & PATTERNS</h1>
<p>Killinkere GAA — 2026 Season · {total} Games Analyzed</p>
<div class="record">
<span class="w">✅ {wins} Wins</span>
<span class="d">➖ {draws} Draw{'s' if draws != 1 else ''}</span>
<span class="l">❌ {losses} Loss{'es' if losses != 1 else ''}</span>
</div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('patterns')">🔍 Key Patterns</div>
<div class="tab" onclick="showTab('charts')">📈 Charts</div>
<div class="tab" onclick="showTab('table')">📋 Game-by-Game</div>
</div>

<div id="patterns" class="tab-content active">

<div class="formula-box">
<h2>🏆 The Winning Formula</h2>
<div class="formula">Score first after half time + Limit opposition to 3 or fewer unanswered scores</div>
<div class="formula-result">= {record(combo_yes)} ({len(combo_yes)} games)</div>
<div style="margin-top:10px;opacity:.8;font-size:.95em">When either condition is broken: {record(combo_no)} ({len(combo_no)} games)</div>
</div>

<h2 style="color:#2c3e50;text-align:center;margin:30px 0 20px;font-size:1.7em">🔍 Pattern Breakdown</h2>

<div class="pattern-grid">

<div class="pattern-card pattern-green">
<h3>🎯 Score First After Half Time</h3>
<div class="insight">When Killinkere score first after the break, the team almost never loses. Both defeats came when the opposition got the first score of the second half.</div>
<div class="record-row">
<div class="rec rec-good">✅ Yes: {record(first_ht_yes)}</div>
<div class="rec rec-bad">❌ No: {record(first_ht_no)}</div>
</div>
</div>

<div class="pattern-card pattern-red">
<h3>🛑 Opposition Scoring Runs (4+)</h3>
<div class="insight">When the opposition strings together 4 or more unanswered scores, Killinkere struggle. Limiting runs to 3 or fewer has meant a perfect record.</div>
<div class="record-row">
<div class="rec rec-good">≤3 run: {record(opp_run_low)}</div>
<div class="rec rec-bad">4+ run: {record(opp_run_high)}</div>
</div>
</div>

<div class="pattern-card pattern-blue">
<h3>⏱️ Win the Second Half</h3>
<div class="insight">Killinkere have never lost a game where they won the second half scoring. Every defeat came when the opposition outscored them after the break.</div>
<div class="record-row">
<div class="rec rec-good">Won 2H: {record(won_2h)}</div>
<div class="rec rec-neutral">Drew 2H: {record(drew_2h)}</div>
<div class="rec rec-bad">Lost 2H: {record(lost_2h)}</div>
</div>
</div>

<div class="pattern-card pattern-purple">
<h3>🏁 Score First Overall</h3>
<div class="insight">Scoring first doesn't guarantee a win — Killinkere have won games where the opposition scored first. It's less predictive than the half-time restart.</div>
<div class="record-row">
<div class="rec rec-good">✅ Yes: {record([g for g in games if g['scored_first']])}</div>
<div class="rec rec-neutral">❌ No: {record([g for g in games if not g['scored_first']])}</div>
</div>
</div>

<div class="pattern-card pattern-gold">
<h3>📊 Half Time Position</h3>
<div class="insight">Being ahead at half time is a strong indicator but not bulletproof — the Arva draw came despite leading by 3 at the break. The team has come from behind at HT twice (v Pearse OG, down 5-7, won 23-13 and v Drung, down 10-11, won 19-16) but the other two deficits ended in defeat.</div>
<div class="record-row">
<div class="rec rec-good">Ahead: {record(ahead_ht)}</div>
<div class="rec rec-neutral">Level: {record(level_ht)}</div>
<div class="rec rec-bad">Behind: {record(behind_ht)}</div>
</div>
</div>

<div class="pattern-card pattern-green">
<h3>🏐 Score Last</h3>
<div class="insight">Killinkere scored last in {sum(1 for g in games if g['scored_last'])} of {total} games — a strong finishing mentality. The only game where they didn't score last and still won was v Liatroim.</div>
<div class="record-row">
<div class="rec rec-good">✅ Yes: {record([g for g in games if g['scored_last']])}</div>
<div class="rec rec-bad">❌ No: {record([g for g in games if not g['scored_last']])}</div>
</div>
</div>

</div>

<h2 style="color:#2c3e50;text-align:center;margin:30px 0 20px;font-size:1.7em">⚠️ Danger Signs</h2>
<div class="pattern-grid">
<div class="pattern-card pattern-red">
<h3>🚨 The Loss Profile</h3>
<div class="insight">Both losses share the same DNA: opposition scored first after half time AND put together a run of 5 unanswered scores. The Arva draw was a near-miss — scored first after HT but allowed a 4-score run.</div>
</div>
<div class="pattern-card pattern-red">
<h3>📉 2nd Half Collapses</h3>
<div class="insight">v Arva: led by 3 at HT, drew. v Greenlough: 2 down at HT, lost by 5. v Denn (Div 3): 6 down at HT, lost by 7. Only comebacks from behind were v Pearse OG (5-7 at HT, won 23-13) and v Drung (10-11 at HT, won 19-16).</div>
</div>
</div>

</div>

<div id="charts" class="tab-content">

<div class="chart-box">
<div class="chart-title">📊 Winning Margin by Game</div>
<canvas id="marginChart"></canvas>
</div>

<div class="chart-box">
<div class="chart-title">⏱️ 2nd Half Scoring — Killinkere vs Opposition</div>
<canvas id="secondHalfChart"></canvas>
</div>

<div class="chart-box">
<div class="chart-title">🔥 Scoring Runs — Killinkere vs Opposition</div>
<canvas id="runsChart"></canvas>
</div>

</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">📋 Game-by-Game Breakdown</h2>
<div style="overflow-x:auto">
<table class="trends-table" id="trendsTable">
<thead><tr>
<th>Date</th><th>Opponent</th><th>Res</th><th>Score</th><th>HT</th><th>1st Score</th><th>1st After HT</th><th>Won 2H</th><th>Opp Run</th><th>Our Run</th><th>Last Score</th><th>Drought</th>
</tr></thead>
<tbody>
{game_rows}
</tbody>
</table>
</div>
</div>

</div>
<div class="footer">Killinkere GAA · Season Trends & Patterns · 2026</div>

<script>
function showTab(t){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active')}}

const labels={chart_labels};
const green='rgba(46,204,113,0.8)',greenB='rgba(39,174,96,1)';
const red='rgba(231,76,60,0.8)',redB='rgba(192,57,43,1)';
const blue='rgba(52,152,219,0.8)',blueB='rgba(41,128,185,1)';

new Chart(document.getElementById('marginChart'),{{
type:'bar',
data:{{labels:labels,datasets:[{{label:'Margin',data:{chart_margins},backgroundColor:{chart_bar_colors},borderColor:{chart_bar_borders},borderWidth:2}}]}},
options:{{responsive:true,scales:{{y:{{title:{{display:true,text:'Points'}}}}}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>{{const r={chart_results}[ctx.dataIndex];return(ctx.parsed.y>0?'+':'')+ctx.parsed.y+' ('+r+')'}}}}}}}}}}
}});

new Chart(document.getElementById('secondHalfChart'),{{
type:'bar',
data:{{labels:labels,datasets:[
{{label:'Killinkere 2H',data:{chart_k_2h},backgroundColor:green,borderColor:greenB,borderWidth:2}},
{{label:'Opposition 2H',data:{chart_o_2h},backgroundColor:red,borderColor:redB,borderWidth:2}}
]}},
options:{{responsive:true,scales:{{y:{{beginAtZero:true,title:{{display:true,text:'Points'}}}}}},plugins:{{legend:{{display:true,position:'top'}}}}}}
}});

new Chart(document.getElementById('runsChart'),{{
type:'bar',
data:{{labels:labels,datasets:[
{{label:'Our Best Run',data:{chart_k_runs},backgroundColor:green,borderColor:greenB,borderWidth:2}},
{{label:'Opp Best Run',data:{chart_opp_runs},backgroundColor:red,borderColor:redB,borderWidth:2}}
]}},
options:{{responsive:true,scales:{{y:{{beginAtZero:true,title:{{display:true,text:'Unanswered Scores'}}}}}},plugins:{{legend:{{display:true,position:'top'}}}}}},
plugins:[{{
id:'dangerLine',
afterDatasetsDraw(chart){{
const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=chart;
const yPos=y.getPixelForValue(4);
ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='rgba(231,76,60,0.6)';ctx.lineWidth=2;
ctx.beginPath();ctx.moveTo(left,yPos);ctx.lineTo(right,yPos);ctx.stroke();
ctx.fillStyle='rgba(231,76,60,0.8)';ctx.font='bold 11px Arial';ctx.textAlign='right';
ctx.fillText('⚠️ Danger zone (4+)',right,yPos-6);
ctx.restore();
}}
}}]
}});

document.querySelectorAll('.trends-table th').forEach((th,i)=>{{
let asc=true;
th.addEventListener('click',()=>{{
const tbody=th.closest('table').querySelector('tbody');
const rows=Array.from(tbody.querySelectorAll('tr'));
rows.sort((a,b)=>{{
let av=a.children[i].textContent.trim();
let bv=b.children[i].textContent.trim();
if(!isNaN(parseFloat(av))&&!isNaN(parseFloat(bv)))return asc?av-bv:bv-av;
return asc?av.localeCompare(bv):bv.localeCompare(av);
}});
rows.forEach(r=>tbody.appendChild(r));
asc=!asc;
}});
}});
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body>
</html>'''

    output = Path(__file__).parent.parent / 'analysis' / 'season_trends.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Generated: {output}")


if __name__ == "__main__":
    generate()
