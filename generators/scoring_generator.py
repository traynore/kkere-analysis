#!/usr/bin/env python3
"""Scoring Report Generator — Season-wide scorer breakdown per game"""
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
        game_idx = len(games)
        games.append({'date': date, 'opponent': opponent, 'competition': comp})

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

    def total_score(player):
        return sum(g['goals'] * 3 + g['points'] + g['two_pts'] * 2 for g in player_stats[player].values())

    def total_goals(player):
        return sum(g['goals'] for g in player_stats[player].values())

    sorted_players = sorted(player_stats.keys(), key=lambda p: (total_score(p), total_goals(p)), reverse=True)

    # Build HTML
    game_headers = ''.join(
        f'<th class="game-col" title="{g["date"]} - {g["competition"]}">{g["opponent"][:8]}</th>'
        for g in games
    )

    rows_html = ''
    for player in sorted_players:
        ts = total_score(player)
        tg = sum(g['goals'] for g in player_stats[player].values())
        tp = sum(g['points'] for g in player_stats[player].values())
        t2 = sum(g['two_pts'] for g in player_stats[player].values())
        games_scored = len(player_stats[player])
        avg = round(ts / len(games), 1)

        cells = ''
        for gi in range(len(games)):
            if gi in player_stats[player]:
                g = player_stats[player][gi]
                score = g['goals'] * 3 + g['points'] + g['two_pts'] * 2
                notation = f"{g['goals']}-{g['points'] + g['two_pts'] * 2}"
                free_marker = 'f' if g['from_frees'] > 0 else ''
                if score >= 5:
                    cell_class = 'hot'
                elif score >= 3:
                    cell_class = 'warm'
                else:
                    cell_class = 'cool'
                cells += f'<td class="game-col {cell_class}" title="{notation} ({g["from_play"]} play, {g["from_frees"]} frees)">{score}{free_marker}</td>'
            else:
                cells += '<td class="game-col empty">-</td>'

        rows_html += f'''<tr>
            <td class="player-name">{player}</td>
            <td class="total-col">{tg}-{tp + t2*2}</td>
            <td class="total-col"><strong>{ts}</strong></td>
            <td class="total-col">{games_scored}</td>
            <td class="total-col">{avg}</td>
            {cells}
        </tr>\n'''

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

        <div class="summary">
            <div class="summary-card">
                <div class="value">{len(sorted_players)}</div>
                <div class="label">Different Scorers</div>
            </div>
            <div class="summary-card">
                <div class="value">{sum(total_score(p) for p in sorted_players)}</div>
                <div class="label">Total Points Scored</div>
            </div>
            <div class="summary-card">
                <div class="value">{sum(total_goals(p) for p in sorted_players)}-{sum(sum(g["points"] + g["two_pts"]*2 for g in player_stats[p].values()) for p in sorted_players)}</div>
                <div class="label">Season Total (G-P)</div>
            </div>
            <div class="summary-card">
                <div class="value">{round(sum(total_score(p) for p in sorted_players) / len(games), 1)}</div>
                <div class="label">Avg Points/Game</div>
            </div>
        </div>

        <div class="card">
            <h2>📊 Scorer Breakdown — Per Game</h2>
            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;padding-left:10px">Player</th>
                        <th>G-P</th>
                        <th>Pts</th>
                        <th>Games</th>
                        <th>Avg</th>
                        {game_headers}
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="legend">
                <span><div class="legend-box" style="background:#d4edda"></div> 5+ pts</span>
                <span><div class="legend-box" style="background:#fff3cd"></div> 3-4 pts</span>
                <span><div class="legend-box" style="background:#e8f4fd"></div> 1-2 pts</span>
                <span>f = includes free(s)</span>
                <span>Hover cells for full breakdown</span>
            </div>
        </div>
    </div>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script></body>
</html>'''

    output = Path(__file__).resolve().parent.parent / 'analysis' / 'scoring.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ Generated: {output}')


if __name__ == '__main__':
    generate()
