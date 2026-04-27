#!/usr/bin/env python3
"""
Opposition Analysis Generator
Reads a game CSV and generates an opposition-focused HTML report.
Usage: python3 opposition_generator.py <csv_file>
"""

import csv
import sys
import json
from pathlib import Path
from collections import defaultdict


def read_csv(filename):
    events = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Team Name'):
                if 'Game Period' in row and 'Period' not in row:
                    row['Period'] = row['Game Period']
                events.append(row)
    return events


def generate_html(csv_file):
    events = read_csv(csv_file)

    all_teams = set(e['Team Name'] for e in events if e.get('Team Name'))
    if 'Killinkere' in all_teams:
        opp = [t for t in all_teams if t != 'Killinkere'][0]
    else:
        teams = sorted(all_teams)
        opp = teams[1]

    opp_events = [e for e in events if e['Team Name'] == opp]

    # Parse score from filename
    stem = Path(csv_file).stem
    import re
    m = re.match(r'(.+?)\s+(\d+)\s*-\s*(\d+)\s+v\s+(\d+)\s*-\s*(\d+)\s+(.+)', stem)
    if m:
        t1_name, t1_g, t1_p, t2_g, t2_p, t2_name = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), m.group(6)
        t1_total = t1_g * 3 + t1_p
        t2_total = t2_g * 3 + t2_p
        result_text = f"{t2_name} {t2_g}-{t2_p} ({t2_total}) v {t1_name} {t1_g}-{t1_p} ({t1_total})"
    else:
        t2_name = opp
        result_text = stem

    # --- SHOTS ---
    shots_play = [e for e in opp_events if e.get('Name') == 'Shot from play']
    shots_free = [e for e in opp_events if e.get('Name') == 'Scoreable free']
    all_shots = shots_play + shots_free

    scored_outcomes = ['Point', 'Goal', '2 Points']
    total_shots = len(all_shots)
    scored = len([s for s in all_shots if s['Outcome'] in scored_outcomes])
    goals = len([s for s in all_shots if s['Outcome'] == 'Goal'])
    points = len([s for s in all_shots if s['Outcome'] == 'Point'])
    two_pts = len([s for s in all_shots if s['Outcome'] == '2 Points'])
    wides = len([s for s in all_shots if s['Outcome'] == 'Wide'])
    shorts = len([s for s in all_shots if s['Outcome'] == 'Short'])
    acc = round(scored / total_shots * 100) if total_shots > 0 else 0
    score_str = f"{goals}-{points + two_pts * 2}"

    play_scored = len([s for s in shots_play if s['Outcome'] in scored_outcomes])
    play_total = len(shots_play)
    play_acc = round(play_scored / play_total * 100) if play_total > 0 else 0
    free_scored = len([s for s in shots_free if s['Outcome'] in scored_outcomes])
    free_total = len(shots_free)
    free_acc = round(free_scored / free_total * 100) if free_total > 0 else 0

    # --- FREE TAKERS ---
    free_takers = defaultdict(lambda: {'attempts': 0, 'scored': 0, 'missed': 0, 'short': 0, 'goals': 0, 'two_pts': 0})
    for s in shots_free:
        p = s.get('Player', 'Unknown')
        free_takers[p]['attempts'] += 1
        if s['Outcome'] in scored_outcomes:
            free_takers[p]['scored'] += 1
            if s['Outcome'] == 'Goal':
                free_takers[p]['goals'] += 1
            elif s['Outcome'] == '2 Points':
                free_takers[p]['two_pts'] += 1
        elif s['Outcome'] == 'Short':
            free_takers[p]['short'] += 1
        else:
            free_takers[p]['missed'] += 1
    free_takers_sorted = sorted(free_takers.items(), key=lambda x: x[1]['attempts'], reverse=True)

    ft_rows = ''
    for name, d in free_takers_sorted:
        ft_acc = round(d['scored'] / d['attempts'] * 100) if d['attempts'] > 0 else 0
        ft_rows += f'<tr><td><strong>{name}</strong></td><td>{d["attempts"]}</td><td>{d["scored"]}</td><td>{d["missed"]}</td><td>{d["short"]}</td><td>{ft_acc}%</td></tr>\n'

    # --- SHOT TIMELINE ---
    timeline_rows = ''
    for s in sorted(all_shots, key=lambda x: (int(x.get('Period', '1')), x.get('Time', ''))):
        shot_type = 'Free' if s['Name'] == 'Scoreable free' else 'Play'
        player = s.get('Player', '—')
        outcome = s['Outcome']
        if outcome == 'Goal':
            badge = '<span class="badge-scored">GOAL ✓</span>'
        elif outcome in ['Point', '2 Points']:
            label = '2 Pointer ✓' if outcome == '2 Points' else 'Point ✓'
            badge = f'<span class="badge-scored">{label}</span>'
        elif outcome == 'Short':
            badge = '<span class="badge-short">Short</span>'
        else:
            badge = f'<span class="badge-missed">{outcome} ✗</span>'

        timeline_rows += f'<tr><td>{s["Time"]}</td><td>{shot_type}</td><td>{player}</td><td>{badge}</td></tr>\n'

        is_last_p1 = s.get('Period') == '1'
        next_shots = [x for x in all_shots if (int(x.get('Period', '1')), x.get('Time', '')) > (int(s.get('Period', '1')), s.get('Time', ''))]
        if is_last_p1 and next_shots and next_shots[0].get('Period') == '2':
            timeline_rows += '<tr style="background:#fff3cd"><td colspan="4" style="text-align:center;font-weight:bold;color:#666">⏱️ HALF TIME</td></tr>\n'

    # --- KICKOUTS ---
    kickouts = [e for e in opp_events if e.get('Name') == 'Kickout']
    ko_total = len(kickouts)
    ko_won_outcomes = ['Won clean', 'Short won', 'Break won']
    ko_lost_outcomes = ['Lost clean', 'Break lost', 'Short lost', 'Sideline ball']
    ko_won = len([k for k in kickouts if k['Outcome'] in ko_won_outcomes])
    ko_lost = ko_total - ko_won
    ko_pct = round(ko_won / ko_total * 100) if ko_total > 0 else 0

    ko_detail_rows = ''
    for k in sorted(kickouts, key=lambda x: (int(x.get('Period', '1')), x.get('Time', ''))):
        player = k.get('Player', '—')
        outcome = k['Outcome']
        if outcome in ko_won_outcomes:
            badge = f'<span class="badge-won">{outcome}</span>'
        else:
            badge = f'<span class="badge-lost">{outcome}</span>'
        ko_detail_rows += f'<tr><td>{k["Time"]}</td><td>{player}</td><td>{badge}</td></tr>\n'

    # Kickout targets
    ko_targets = defaultdict(lambda: {'total': 0, 'won': 0, 'lost': 0})
    for k in kickouts:
        p = k.get('Player', '—')
        ko_targets[p]['total'] += 1
        if k['Outcome'] in ko_won_outcomes:
            ko_targets[p]['won'] += 1
        else:
            ko_targets[p]['lost'] += 1
    ko_targets_sorted = sorted(ko_targets.items(), key=lambda x: x[1]['total'], reverse=True)

    kt_rows = ''
    for name, d in ko_targets_sorted:
        wpct = round(d['won'] / d['total'] * 100) if d['total'] > 0 else 0
        color = '#27ae60' if wpct >= 60 else '#e74c3c' if wpct <= 40 else '#2c3e50'
        kt_rows += f'<tr><td><strong>{name}</strong></td><td>{d["total"]}</td><td>{d["won"]}</td><td>{d["lost"]}</td><td style="color:{color};font-weight:bold">{wpct}%</td></tr>\n'

    # --- SCORING BY HALF ---
    p1_shots = [s for s in all_shots if s.get('Period') == '1']
    p2_shots = [s for s in all_shots if s.get('Period') == '2']
    p1_scored = len([s for s in p1_shots if s['Outcome'] in scored_outcomes])
    p2_scored = len([s for s in p2_shots if s['Outcome'] in scored_outcomes])
    p1_from_play = len([s for s in p1_shots if s['Name'] == 'Shot from play' and s['Outcome'] in scored_outcomes])
    p2_from_play = len([s for s in p2_shots if s['Name'] == 'Shot from play' and s['Outcome'] in scored_outcomes])

    # --- CHART DATA ---
    chart_labels = []
    chart_data = []
    chart_colors = []
    if goals > 0:
        chart_labels.append(f'Goals ({goals})')
        chart_data.append(goals)
        chart_colors.append('#16a085')
    play_pts = len([s for s in shots_play if s['Outcome'] == 'Point'])
    if play_pts > 0:
        chart_labels.append(f'Points from Play ({play_pts})')
        chart_data.append(play_pts)
        chart_colors.append('#2ecc71')
    free_pts = len([s for s in shots_free if s['Outcome'] == 'Point'])
    if free_pts > 0:
        chart_labels.append(f'Points from Frees ({free_pts})')
        chart_data.append(free_pts)
        chart_colors.append('#27ae60')
    all_two = len([s for s in all_shots if s['Outcome'] == '2 Points'])
    if all_two > 0:
        chart_labels.append(f'2 Pointers ({all_two})')
        chart_data.append(all_two)
        chart_colors.append('#1abc9c')
    missed_total = total_shots - scored
    if missed_total > 0:
        chart_labels.append(f'Missed ({missed_total})')
        chart_data.append(missed_total)
        chart_colors.append('#e74c3c')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{opp} — Opposition Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#2c3e50 0%,#3498db 100%);min-height:100vh;padding:20px}}
.container{{max-width:900px;margin:0 auto}}
.header{{background:linear-gradient(135deg,#c0392b 0%,#e74c3c 100%);color:#fff;padding:35px;border-radius:20px 20px 0 0;text-align:center}}
.header h1{{font-size:2.2em;margin-bottom:5px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header .subtitle{{font-size:1.1em;opacity:.9}}
.header .result{{font-size:1.4em;font-weight:bold;margin-top:10px}}
.content{{background:#fff;padding:30px;border-radius:0 0 20px 20px;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.section{{margin-bottom:30px}}
.section-title{{font-size:1.3em;color:#2c3e50;margin-bottom:15px;padding-bottom:8px;border-bottom:3px solid #e74c3c}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}}
.stat-box{{background:linear-gradient(135deg,#f8f9fa,#e9ecef);border-radius:12px;padding:15px;text-align:center;border-left:4px solid #e74c3c}}
.stat-box .number{{font-size:2em;font-weight:bold;color:#2c3e50}}
.stat-box .label{{font-size:.8em;color:#666;margin-top:4px}}
.chart-container{{background:#f8f9fa;border-radius:12px;padding:20px;margin-bottom:15px}}
.chart-container canvas{{max-height:300px}}
table{{width:100%;border-collapse:collapse;margin-top:10px}}
th{{background:linear-gradient(135deg,#2c3e50,#34495e);color:#fff;padding:10px 12px;text-align:left;font-size:.85em}}
td{{padding:9px 12px;border-bottom:1px solid #eee;font-size:.9em}}
tr:hover{{background:#f8f9fa}}
.badge-scored{{background:#27ae60;color:#fff;padding:2px 8px;border-radius:8px;font-size:.8em;font-weight:bold}}
.badge-missed{{background:#e74c3c;color:#fff;padding:2px 8px;border-radius:8px;font-size:.8em;font-weight:bold}}
.badge-short{{background:#f39c12;color:#fff;padding:2px 8px;border-radius:8px;font-size:.8em;font-weight:bold}}
.badge-won{{background:#27ae60;color:#fff;padding:2px 8px;border-radius:8px;font-size:.8em;font-weight:bold}}
.badge-lost{{background:#e74c3c;color:#fff;padding:2px 8px;border-radius:8px;font-size:.8em;font-weight:bold}}
.insight{{background:linear-gradient(135deg,#fff3cd,#ffeaa7);border-left:4px solid #f39c12;padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:10px;font-size:.9em}}
.insight strong{{color:#e67e22}}
.bar-row{{display:flex;align-items:center;margin-bottom:8px}}
.bar-label{{width:120px;font-size:.85em;font-weight:bold;color:#2c3e50}}
.bar-track{{flex:1;height:28px;background:#eee;border-radius:14px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:14px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:.8em;min-width:40px}}
.bar-fill.scored{{background:linear-gradient(90deg,#27ae60,#2ecc71)}}
.bar-fill.missed{{background:linear-gradient(90deg,#e74c3c,#c0392b)}}
.bar-fill.won{{background:linear-gradient(90deg,#27ae60,#2ecc71)}}
.bar-fill.lost{{background:linear-gradient(90deg,#e74c3c,#c0392b)}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:600px){{.two-col{{grid-template-columns:1fr}}.stat-grid{{grid-template-columns:repeat(2,1fr)}}}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.85em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>\U0001f50d {opp}</h1>
<div class="subtitle">Opposition Analysis</div>
<div class="result">{result_text}</div>
</div>
<div class="content">

<div class="section">
<div class="section-title">\U0001f3af Shots Overview</div>
<div class="stat-grid">
<div class="stat-box"><div class="number">{total_shots}</div><div class="label">Total Shots</div></div>
<div class="stat-box"><div class="number">{scored}</div><div class="label">Scored</div></div>
<div class="stat-box"><div class="number">{acc}%</div><div class="label">Accuracy</div></div>
<div class="stat-box"><div class="number">{score_str}</div><div class="label">Total Score</div></div>
</div>
<div class="chart-container"><canvas id="shotBreakdownChart"></canvas></div>
<div class="two-col">
<div>
<h4 style="margin-bottom:8px;color:#2c3e50">From Play ({play_total})</h4>
<div class="bar-row"><div class="bar-label">Scored ({play_scored})</div><div class="bar-track"><div class="bar-fill scored" style="width:{play_acc}%">{play_acc}%</div></div></div>
<div class="bar-row"><div class="bar-label">Missed ({play_total - play_scored})</div><div class="bar-track"><div class="bar-fill missed" style="width:{100 - play_acc}%">{100 - play_acc}%</div></div></div>
</div>
<div>
<h4 style="margin-bottom:8px;color:#2c3e50">From Frees/Dead Balls ({free_total})</h4>
<div class="bar-row"><div class="bar-label">Scored ({free_scored})</div><div class="bar-track"><div class="bar-fill scored" style="width:{free_acc}%">{free_acc}%</div></div></div>
<div class="bar-row"><div class="bar-label">Missed ({free_total - free_scored})</div><div class="bar-track"><div class="bar-fill missed" style="width:{100 - free_acc}%">{100 - free_acc}%</div></div></div>
</div>
</div>
</div>

<div class="section">
<div class="section-title">\U0001f9b6 Free Takers</div>
<table>
<thead><tr><th>Player</th><th>Attempts</th><th>Scored</th><th>Missed</th><th>Short</th><th>Accuracy</th></tr></thead>
<tbody>{ft_rows}</tbody>
</table>
</div>

<div class="section">
<div class="section-title">\u23f1\ufe0f Shot Timeline</div>
<table>
<thead><tr><th>Time</th><th>Type</th><th>Player</th><th>Result</th></tr></thead>
<tbody>{timeline_rows}</tbody>
</table>
</div>

<div class="section">
<div class="section-title">\U0001f3d0 Kickout Analysis</div>
<div class="stat-grid">
<div class="stat-box"><div class="number">{ko_total}</div><div class="label">Total Kickouts</div></div>
<div class="stat-box"><div class="number">{ko_won}</div><div class="label">Won</div></div>
<div class="stat-box"><div class="number">{ko_lost}</div><div class="label">Lost</div></div>
<div class="stat-box"><div class="number" style="color:{'#27ae60' if ko_pct >= 50 else '#e74c3c'}">{ko_pct}%</div><div class="label">Win Rate</div></div>
</div>
</div>

<div class="section">
<div class="section-title">\U0001f3af Kickout Targets</div>
<table>
<thead><tr><th>Player</th><th>Times Targeted</th><th>Won</th><th>Lost</th><th>Win %</th></tr></thead>
<tbody>{kt_rows}</tbody>
</table>
</div>

<div class="section">
<div class="section-title">\U0001f4cb Kickout Detail</div>
<table>
<thead><tr><th>Time</th><th>Target</th><th>Result</th></tr></thead>
<tbody>{ko_detail_rows}</tbody>
</table>
</div>

<div class="section">
<div class="section-title">\u23f1\ufe0f Scoring by Half</div>
<div class="stat-grid">
<div class="stat-box"><div class="number">{p1_scored}</div><div class="label">1st Half Scores</div></div>
<div class="stat-box"><div class="number">{p1_from_play}</div><div class="label">1H From Play</div></div>
<div class="stat-box"><div class="number">{p2_scored}</div><div class="label">2nd Half Scores</div></div>
<div class="stat-box"><div class="number">{p2_from_play}</div><div class="label">2H From Play</div></div>
</div>
</div>

<div class="section">
<div class="section-title">\U0001f4dd Tactical Takeaways</div>
<div class="insight"><strong>Add your tactical notes here based on the data above.</strong></div>
</div>

</div>
<div class="footer">{opp} Opposition Analysis \u00b7 Killinkere GAA 2026</div>
</div>

<script>
new Chart(document.getElementById('shotBreakdownChart'),{{
type:'doughnut',
data:{{labels:{json.dumps(chart_labels)},datasets:[{{data:{json.dumps(chart_data)},backgroundColor:{json.dumps(chart_colors)}}}]}},
options:{{responsive:true,plugins:{{legend:{{position:'right',labels:{{font:{{size:11}}}}}},title:{{display:true,text:'Shot Outcomes Breakdown',font:{{size:14}}}}}}}}
}});
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body>
</html>'''

    output_file = str(Path(csv_file).parent / f"{opp.lower().replace(' ', '-')}-opposition.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Generated: {output_file}")
    return output_file


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 opposition_generator.py <csv_file>")
        sys.exit(1)
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    generate_html(csv_file)
