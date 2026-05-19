#!/usr/bin/env python3
"""Scoring Report Generator — Season-wide scorer breakdown per game, filterable by competition"""
import csv, json, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def read_csv(f):
    events = []
    with open(f, 'r', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row.get('Team Name'):
                if 'Game Period' in row and 'Period' not in row:
                    row['Period'] = row['Game Period']
                events.append(row)
    return events


def read_meta(f):
    meta = {}
    mf = Path(f).with_suffix('.meta')
    if not mf.exists():
        stem = Path(f).stem
        for c in Path(f).parent.glob('*.meta'):
            if c.stem.replace(' ', '') == stem.replace(' ', ''):
                mf = c
                break
    if mf.exists():
        with open(mf, 'r', encoding='utf-8') as fh:
            for line in fh:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    meta[k] = v
    return meta


def categorise(comp):
    c = comp.lower()
    if 'spring' in c or 'ulster' in c:
        return 'Spring League'
    elif 'challenge' in c:
        return 'Challenge'
    elif 'div 3' in c or 'div3' in c or 'rnd' in c and '3' in c:
        return 'ACFL Div 3'
    elif 'div 5' in c or 'div5' in c or 'div 7' in c or 'div7' in c or 'reserve' in c:
        return 'ACFL Div 7'
    else:
        return 'Other'


def generate():
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    all_csvs = sorted(data_dir.glob('Killinkere*.csv'),
                      key=lambda p: datetime.strptime(read_meta(str(p)).get('date', '01/01/2099'), '%d/%m/%Y')
                      if read_meta(str(p)).get('date') else datetime.max)

    games = []
    player_stats = defaultdict(lambda: defaultdict(lambda: {'goals': 0, 'points': 0, 'two_pts': 0, 'from_play': 0, 'from_frees': 0}))

    for csv_path in all_csvs:
        events = read_csv(str(csv_path))
        meta = read_meta(str(csv_path))

        match = re.search(r'v\s+\d+\s*-\s*\d+\s+(.+)\.csv', csv_path.name)
        opponent = match.group(1).strip() if match else csv_path.stem
        date = meta.get('date', '')
        comp = meta.get('competition', '')
        category = categorise(comp)
        game_idx = len(games)
        games.append({'date': date, 'opponent': opponent, 'competition': comp, 'category': category})

        scoring = [e for e in events if e['Team Name'] == 'Killinkere'
                   and e.get('Player')
                   and e.get('Name') in ['Shot from play', 'Scoreable free']
                   and e.get('Outcome') in ['Goal', 'Point', '2 Points']]

        for e in scoring:
            player = e['Player']
            s = player_stats[player][game_idx]
            if e['Outcome'] == 'Goal':
                s['goals'] += 1
            elif e['Outcome'] == 'Point':
                s['points'] += 1
            elif e['Outcome'] == '2 Points':
                s['two_pts'] += 1
            if e['Name'] == 'Shot from play':
                s['from_play'] += 1
            else:
                s['from_frees'] += 1

    # Categories for tabs
    categories = ['All', 'Spring League', 'Challenge', 'ACFL Div 3', 'ACFL Div 7']

    # JSON data for JS filtering
    games_json = json.dumps([{'opponent': g['opponent'], 'date': g['date'], 'competition': g['competition'], 'category': g['category']} for g in games])

    players_json_data = []
    for player in player_stats:
        p_data = {'name': player, 'games': {}}
        for gi, g in player_stats[player].items():
            p_data['games'][str(gi)] = g
        players_json_data.append(p_data)
    players_json = json.dumps(players_json_data)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Killinkere GAA — Scoring Report 2026</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 30px; border-radius: 16px; text-align: center; margin-bottom: 24px; }}
        .header h1 {{ font-size: 2em; margin-bottom: 4px; }}
        .header p {{ opacity: 0.8; font-size: 1em; }}
        .tabs {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 20px; }}
        .tab {{ padding: 10px 18px; border-radius: 8px; border: 2px solid #dee2e6; background: white; cursor: pointer; font-weight: 600; font-size: 0.9em; transition: all 0.2s; }}
        .tab:hover {{ border-color: #1e3c72; color: #1e3c72; }}
        .tab.active {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; border-color: #1e3c72; }}
        .card {{ background: white; border-radius: 14px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 24px; overflow-x: auto; }}
        .card h2 {{ color: #1e3c72; margin-bottom: 16px; font-size: 1.3em; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 0.82em; }}
        th {{ background: #f8f9fa; padding: 8px 6px; text-align: center; border-bottom: 2px solid #dee2e6; white-space: nowrap; }}
        td {{ padding: 7px 6px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
        .player-name {{ text-align: left; font-weight: 600; white-space: nowrap; position: sticky; left: 0; background: white; z-index: 1; padding-left: 10px; }}
        .total-col {{ font-weight: 600; background: #f8f9fa; }}
        .game-col {{ min-width: 42px; font-size: 0.9em; }}
        .game-col.hot {{ background: #d4edda; color: #155724; font-weight: bold; }}
        .game-col.warm {{ background: #fff3cd; color: #856404; }}
        .game-col.cool {{ background: #e8f4fd; color: #0c5460; }}
        .game-col.empty {{ color: #ccc; }}
        tr:hover td {{ background: #f0f7ff; }}
        tr:hover .player-name {{ background: #f0f7ff; }}
        .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 14px; font-size: 0.85em; color: #666; }}
        .legend span {{ display: flex; align-items: center; gap: 4px; }}
        .legend-box {{ width: 14px; height: 14px; border-radius: 3px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px; }}
        .summary-card {{ background: white; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }}
        .summary-card .value {{ font-size: 2em; font-weight: bold; color: #1e3c72; }}
        .summary-card .label {{ font-size: 0.85em; color: #666; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏐 Scoring Report</h1>
            <p>Killinkere GAA — 2026 Season · All Scorers Game-by-Game</p>
        </div>

        <div class="tabs" id="comp-tabs">
            <div class="tab active" data-cat="All">All</div>
            <div class="tab" data-cat="Spring League">🏆 Spring League</div>
            <div class="tab" data-cat="Challenge">⚔️ Challenge</div>
            <div class="tab" data-cat="ACFL Div 3">📋 ACFL Div 3</div>
            <div class="tab" data-cat="ACFL Div 7">📋 ACFL Div 7</div>
        </div>

        <div class="summary" id="summary"></div>

        <div class="card">
            <h2>📊 Scorer Breakdown — Per Game</h2>
            <div id="table-container"></div>
            <div class="legend">
                <span><div class="legend-box" style="background:#d4edda"></div> 5+ pts</span>
                <span><div class="legend-box" style="background:#fff3cd"></div> 3-4 pts</span>
                <span><div class="legend-box" style="background:#e8f4fd"></div> 1-2 pts</span>
                <span>f = includes free(s)</span>
                <span>Hover cells for full breakdown</span>
            </div>
        </div>
    </div>

<script>
var games = {games_json};
var players = {players_json};

function render(cat) {{
    var indices = [];
    for (var i = 0; i < games.length; i++) {{
        if (cat === 'All' || games[i].category === cat) indices.push(i);
    }}

    // Calculate per-player totals for this filter
    var playerTotals = players.map(function(p) {{
        var goals = 0, pts = 0, two = 0, fromPlay = 0, fromFrees = 0, gamesScored = 0;
        indices.forEach(function(gi) {{
            var g = p.games[gi];
            if (g) {{
                goals += g.goals;
                pts += g.points;
                two += g.two_pts;
                fromPlay += g.from_play;
                fromFrees += g.from_frees;
                gamesScored++;
            }}
        }});
        var total = goals * 3 + pts + two * 2;
        return {{name: p.name, goals: goals, pts: pts, two: two, total: total, gamesScored: gamesScored, games: p.games}};
    }}).filter(function(p) {{ return p.total > 0; }});

    playerTotals.sort(function(a, b) {{ return b.total - a.total || b.goals - a.goals; }});

    // Summary
    var totalScorers = playerTotals.length;
    var totalPts = playerTotals.reduce(function(s, p) {{ return s + p.total; }}, 0);
    var totalGoals = playerTotals.reduce(function(s, p) {{ return s + p.goals; }}, 0);
    var totalPoints = playerTotals.reduce(function(s, p) {{ return s + p.pts + p.two * 2; }}, 0);
    var avgPerGame = indices.length > 0 ? (totalPts / indices.length).toFixed(1) : 0;

    document.getElementById('summary').innerHTML =
        '<div class="summary-card"><div class="value">' + totalScorers + '</div><div class="label">Different Scorers</div></div>' +
        '<div class="summary-card"><div class="value">' + totalPts + '</div><div class="label">Total Points Scored</div></div>' +
        '<div class="summary-card"><div class="value">' + totalGoals + '-' + totalPoints + '</div><div class="label">Total (G-P)</div></div>' +
        '<div class="summary-card"><div class="value">' + avgPerGame + '</div><div class="label">Avg Points/Game</div></div>';

    // Table
    var headers = '<th style="text-align:left;padding-left:10px">Player</th><th>G-P</th><th>Pts</th><th>Games</th><th>Avg</th>';
    indices.forEach(function(gi) {{
        headers += '<th class="game-col" title="' + games[gi].date + ' - ' + games[gi].competition + '">' + games[gi].opponent.substring(0, 8) + '</th>';
    }});

    var rows = '';
    playerTotals.forEach(function(p) {{
        var avg = indices.length > 0 ? (p.total / indices.length).toFixed(1) : 0;
        var cells = '';
        indices.forEach(function(gi) {{
            var g = p.games[gi];
            if (g) {{
                var score = g.goals * 3 + g.points + g.two_pts * 2;
                var notation = g.goals + '-' + (g.points + g.two_pts * 2);
                var fm = g.from_frees > 0 ? 'f' : '';
                var cls = score >= 5 ? 'hot' : score >= 3 ? 'warm' : 'cool';
                cells += '<td class="game-col ' + cls + '" title="' + notation + ' (' + g.from_play + ' play, ' + g.from_frees + ' frees)">' + score + fm + '</td>';
            }} else {{
                cells += '<td class="game-col empty">-</td>';
            }}
        }});
        rows += '<tr><td class="player-name">' + p.name + '</td><td class="total-col">' + p.goals + '-' + (p.pts + p.two * 2) + '</td><td class="total-col"><strong>' + p.total + '</strong></td><td class="total-col">' + p.gamesScored + '</td><td class="total-col">' + avg + '</td>' + cells + '</tr>';
    }});

    document.getElementById('table-container').innerHTML = '<table><thead><tr>' + headers + '</tr></thead><tbody>' + rows + '</tbody></table>';
}}

// Tab click handlers
document.querySelectorAll('.tab').forEach(function(tab) {{
    tab.addEventListener('click', function() {{
        document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
        tab.classList.add('active');
        render(tab.getAttribute('data-cat'));
    }});
}});

render('All');
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script></body>
</html>'''

    output = Path(__file__).resolve().parent.parent / 'analysis' / 'scoring.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ Generated: {output}')


if __name__ == '__main__':
    generate()
