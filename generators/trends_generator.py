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
                if 'Game Period' in row and 'Period' not in row:
                    row['Period'] = row['Game Period']
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

    # Scoring droughts - longest gap between Killinkere scores (per half)
    k_score_times_h1 = []
    k_score_times_h2 = []
    for e in all_scores:
        if e['Team Name'] == 'Killinkere' and e.get('Time'):
            t = e['Time']
            parts = t.split(':')
            if len(parts) == 3:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                if e.get('Period') == '1':
                    k_score_times_h1.append(secs)
                else:
                    k_score_times_h2.append(secs)
    longest_drought = 0
    for times in [k_score_times_h1, k_score_times_h2]:
        for i in range(1, len(times)):
            gap = times[i] - times[i - 1]
            longest_drought = max(longest_drought, gap)

    date_str = meta.get('date', '')
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        date_obj = datetime.max

    # Shooting stats
    ke = [e for e in events if e['Team Name'] == 'Killinkere']
    shots = [e for e in ke if e.get('Name') == 'Shot from play']
    shots_scored = [s for s in shots if s['Outcome'] in ['Goal', 'Point', '2 Points']]
    shot_acc = round(len(shots_scored) / len(shots) * 100, 1) if shots else 0
    wides = len([s for s in shots if s['Outcome'] == 'Wide'])

    attacks = [e for e in ke if e.get('Name') == 'Attacks']
    attacks_shot = [a for a in attacks if a['Outcome'] == 'Shot taken']
    has_attack_data = len(attacks_shot) > 0
    attack_eff = round(len(attacks_shot) / len(attacks) * 100, 1) if attacks else 0

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
        'shot_acc': shot_acc,
        'total_shots': len(shots),
        'total_scored': len(shots_scored),
        'wides': wides,
        'attack_eff': attack_eff,
        'total_attacks': len(attacks),
        'attacks_shot': len(attacks_shot),
        'has_attack_data': has_attack_data,
    }


def analyze_scoring(data_dir):
    """Analyze all scoring across the season for player and source breakdowns, per competition."""
    from collections import defaultdict

    # Per-game scoring records with competition tag
    game_records = []  # list of {comp, player, goals, points, 2pts, frees, play}

    for f in sorted(data_dir.glob('Killinkere*.csv')):
        meta = read_meta(f)
        comp = meta.get('competition', '')
        events = read_csv(f)
        game_scorers = set()

        for e in events:
            team = e.get('Team Name', '')
            name = e.get('Name', '')
            outcome = e.get('Outcome', '')
            player = (e.get('Player') or '').strip() or 'Unknown'

            if team == 'Killinkere' and name in ['Shot from play', 'Scoreable free'] and outcome in ['Goal', 'Point', '2 Points']:
                is_free = name == 'Scoreable free'
                game_records.append({
                    'comp': comp,
                    'file': str(f),
                    'player': player,
                    'outcome': outcome,
                    'is_free': is_free,
                })
                game_scorers.add(player)

    def summarize(records):
        player_stats = defaultdict(lambda: {'points': 0, 'goals': 0, '2pts': 0, 'frees': 0, 'play': 0, 'games': set(), 'total_pts': 0})
        total_goals = 0
        total_points = 0
        total_2pts = 0
        total_from_play = 0
        total_from_frees = 0
        games_seen = defaultdict(set)  # player -> set of files
        all_games = set()

        for r in records:
            player = r['player']
            outcome = r['outcome']
            pts_val = 3 if outcome == 'Goal' else (2 if outcome == '2 Points' else 1)
            player_stats[player]['total_pts'] += pts_val
            player_stats[player]['games'].add(r['file'])
            all_games.add(r['file'])

            if outcome == 'Goal':
                player_stats[player]['goals'] += 1
                total_goals += 1
            elif outcome == '2 Points':
                player_stats[player]['2pts'] += 1
                total_2pts += 1
            else:
                player_stats[player]['points'] += 1
                total_points += 1

            if r['is_free']:
                player_stats[player]['frees'] += 1
                total_from_frees += 1
            else:
                player_stats[player]['play'] += 1
                total_from_play += 1

        total_value = total_goals * 3 + total_points + total_2pts * 2
        total_scores = total_goals + total_points + total_2pts

        # Avg scorers per game
        game_scorer_counts = defaultdict(set)
        for r in records:
            game_scorer_counts[r['file']].add(r['player'])
        avg_scorers = round(sum(len(v) for v in game_scorer_counts.values()) / len(game_scorer_counts), 1) if game_scorer_counts else 0

        sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['total_pts'], reverse=True)
        return {
            'players': sorted_players,
            'total_goals': total_goals,
            'total_points': total_points,
            'total_2pts': total_2pts,
            'total_from_play': total_from_play,
            'total_from_frees': total_from_frees,
            'total_value': total_value,
            'total_scores': total_scores,
            'avg_scorers_per_game': avg_scorers,
            'num_games': len(all_games),
        }

    # Build JSON-friendly per-competition data
    def comp_category(comp):
        c = comp.lower()
        if 'spring' in c or 'ulster' in c: return 'Spring League'
        elif 'challenge' in c: return 'Challenge'
        elif 'div 3' in c or 'div3' in c: return 'ACFL Div 3'
        else: return 'ACFL Div 7'

    all_summary = summarize(game_records)

    # Per-comp JSON data for JS filtering
    comp_data = {}
    comps_used = set(comp_category(r['comp']) for r in game_records)
    for comp in sorted(comps_used):
        comp_records = [r for r in game_records if comp_category(r['comp']) == comp]
        s = summarize(comp_records)
        players_json = []
        for player, stats in s['players']:
            if player == 'Unknown':
                continue
            players_json.append({
                'player': player,
                'games': len(stats['games']),
                'total': stats['total_pts'],
                'avg': round(stats['total_pts'] / len(stats['games']), 1),
                'goals': stats['goals'],
                'points': stats['points'],
                '2pts': stats['2pts'],
                'play': stats['play'],
                'frees': stats['frees'],
            })
        comp_data[comp] = {
            'players': players_json,
            'total_goals': s['total_goals'],
            'total_points': s['total_points'],
            'total_2pts': s['total_2pts'],
            'total_from_play': s['total_from_play'],
            'total_from_frees': s['total_from_frees'],
            'total_value': s['total_value'],
            'total_scores': s['total_scores'],
            'avg_scorers_per_game': s['avg_scorers_per_game'],
            'num_scorers': len([p for p in s['players'] if p[0] != 'Unknown']),
        }

    # Also build 'All' entry
    all_players_json = []
    for player, stats in all_summary['players']:
        if player == 'Unknown':
            continue
        all_players_json.append({
            'player': player,
            'games': len(stats['games']),
            'total': stats['total_pts'],
            'avg': round(stats['total_pts'] / len(stats['games']), 1),
            'goals': stats['goals'],
            'points': stats['points'],
            '2pts': stats['2pts'],
            'play': stats['play'],
            'frees': stats['frees'],
        })
    comp_data['All'] = {
        'players': all_players_json,
        'total_goals': all_summary['total_goals'],
        'total_points': all_summary['total_points'],
        'total_2pts': all_summary['total_2pts'],
        'total_from_play': all_summary['total_from_play'],
        'total_from_frees': all_summary['total_from_frees'],
        'total_value': all_summary['total_value'],
        'total_scores': all_summary['total_scores'],
        'avg_scorers_per_game': all_summary['avg_scorers_per_game'],
        'num_scorers': len(all_players_json),
    }

    all_summary['comp_data_json'] = json.dumps(comp_data)
    return all_summary


def generate():
    data_dir = Path(__file__).parent.parent / 'data'
    games = []
    for f in sorted(data_dir.glob('*.csv')):
        g = analyze_game(f)
        if g:
            games.append(g)

    games.sort(key=lambda g: g['date_obj'])

    # Scoring analysis
    scoring = analyze_scoring(data_dir)

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
    drought_short = [g for g in games if g['longest_drought_mins'] <= 12]
    drought_long = [g for g in games if g['longest_drought_mins'] > 12]
    behind_no_faht = [g for g in games if g['ht_lead'] < 0 and not g['scored_first_after_ht']]
    behind_yes_faht = [g for g in games if g['ht_lead'] < 0 and g['scored_first_after_ht']]

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

    # Shooting patterns (only games with attack data)
    games_with_attacks = [g for g in games if g['has_attack_data']]
    acc_above_50 = [g for g in games if g['shot_acc'] >= 50]
    acc_below_50 = [g for g in games if g['shot_acc'] < 50]
    att_above_80 = [g for g in games_with_attacks if g['attack_eff'] >= 80]
    att_below_80 = [g for g in games_with_attacks if g['attack_eff'] < 80]
    shooting_combo_yes = [g for g in games_with_attacks if g['shot_acc'] >= 50 and g['attack_eff'] >= 80]
    shooting_combo_no = [g for g in games_with_attacks if g['shot_acc'] < 50 or g['attack_eff'] < 80]

    # Scoring breakdown HTML
    play_pct = round(scoring['total_from_play'] / scoring['total_scores'] * 100) if scoring['total_scores'] else 0
    free_pct = 100 - play_pct
    goal_pts_pct = round(scoring['total_goals'] * 3 / scoring['total_value'] * 100) if scoring['total_value'] else 0
    point_pts_pct = round(scoring['total_points'] / scoring['total_value'] * 100) if scoring['total_value'] else 0
    two_pts_pct = round(scoring['total_2pts'] * 2 / scoring['total_value'] * 100) if scoring['total_value'] else 0

    scorer_rows = ''
    for player, stats in scoring['players']:
        if player == 'Unknown':
            continue
        games_played = len(stats['games'])
        avg = round(stats['total_pts'] / games_played, 1)
        scorer_rows += f'''<tr>
<td style="text-align:left;font-weight:bold">{player}</td>
<td>{games_played}</td>
<td style="font-weight:bold;color:#2a5298">{stats['total_pts']}</td>
<td>{avg}</td>
<td>{stats['goals']}</td>
<td>{stats['points']}</td>
<td>{stats['2pts']}</td>
<td>{stats['play']}</td>
<td>{stats['frees']}</td>
</tr>
'''

    # Chart data for shooting
    chart_acc = json.dumps([g['shot_acc'] for g in games])
    chart_att_eff = json.dumps([g['attack_eff'] for g in games_with_attacks])
    chart_att_labels = json.dumps([f"v {g['opponent']}" for g in games_with_attacks])
    chart_att_colors = json.dumps(['rgba(46,204,113,0.8)' if g['result'] == 'W' else ('rgba(231,76,60,0.8)' if g['result'] == 'L' else 'rgba(243,156,18,0.8)') for g in games_with_attacks])
    chart_att_borders = json.dumps(['rgba(39,174,96,1)' if g['result'] == 'W' else ('rgba(192,57,43,1)' if g['result'] == 'L' else 'rgba(230,126,34,1)') for g in games_with_attacks])
    chart_wides = json.dumps([g['wides'] for g in games])

    # Competition categories for filtering
    def comp_category(comp):
        c = comp.lower()
        if 'spring' in c or 'ulster' in c: return 'Spring League'
        elif 'challenge' in c: return 'Challenge'
        elif 'div 3' in c or 'div3' in c: return 'ACFL Div 3'
        else: return 'ACFL Div 7'
    chart_comps = json.dumps([comp_category(g['competition']) for g in games])
    chart_att_comps = json.dumps([comp_category(g['competition']) for g in games_with_attacks])

    # Scatter data: accuracy vs attack efficiency
    scatter_data = json.dumps([{'x': g['attack_eff'], 'y': g['shot_acc'], 'label': f"v {g['opponent']}"} for g in games_with_attacks])
    scatter_colors = json.dumps(['rgba(46,204,113,0.9)' if g['result'] == 'W' else ('rgba(231,76,60,0.9)' if g['result'] == 'L' else 'rgba(243,156,18,0.9)') for g in games_with_attacks])

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
.comp-filter{{padding:8px 16px;border:2px solid #2a5298;border-radius:20px;background:#fff;color:#2a5298;font-weight:bold;font-size:.9em;cursor:pointer;margin:4px;transition:.2s}}
.comp-filter:hover{{background:#eef2ff}}
.comp-filter.active{{background:#2a5298;color:#fff}}
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
<div class="tab" onclick="showTab('shooting')">🎯 Shooting</div>
<div class="tab" onclick="showTab('table')">📋 Game-by-Game</div>
</div>

<div id="patterns" class="tab-content active">
<div style="text-align:center;padding:60px 20px;color:#7f8c8d">
<div style="font-size:3em;margin-bottom:15px">🔍</div>
<h2 style="color:#2c3e50;margin-bottom:10px">Coming Soon</h2>
<p style="font-size:1.1em">Key patterns and insights will be added here.</p>
</div>
</div>

<div id="charts" class="tab-content">

<div style="text-align:center;margin-bottom:25px">
<span style="font-weight:bold;color:#2c3e50;margin-right:12px">Filter:</span>
<button class="comp-filter active" onclick="filterCharts('All')">All</button>
<button class="comp-filter" onclick="filterCharts('Spring League')">Spring League</button>
<button class="comp-filter" onclick="filterCharts('Challenge')">Challenge</button>
<button class="comp-filter" onclick="filterCharts('ACFL Div 3')">ACFL Div 3</button>
<button class="comp-filter" onclick="filterCharts('ACFL Div 7')">ACFL Div 7</button>
</div>

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

<div id="shooting" class="tab-content">

<div style="text-align:center;margin-bottom:25px">
<span style="font-weight:bold;color:#2c3e50;margin-right:12px">Filter:</span>
<button class="comp-filter active" onclick="filterAll('All')">All</button>
<button class="comp-filter" onclick="filterAll('Spring League')">Spring League</button>
<button class="comp-filter" onclick="filterAll('Challenge')">Challenge</button>
<button class="comp-filter" onclick="filterAll('ACFL Div 3')">ACFL Div 3</button>
<button class="comp-filter" onclick="filterAll('ACFL Div 7')">ACFL Div 7</button>
</div>

<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">🏆 Season Scoring Breakdown</h2>

<div class="summary-row" id="scoringSummary">
<div class="summary-card"><div class="val" id="scTotalVal">{scoring['total_value']}</div><div class="lbl">Total Points Scored</div></div>
<div class="summary-card"><div class="val" id="scGoalsPts">{scoring['total_goals']}-{scoring['total_points']}</div><div class="lbl">Goals & Points</div></div>
<div class="summary-card"><div class="val" id="sc2Pts">{scoring['total_2pts']}</div><div class="lbl">2-Pointers</div></div>
<div class="summary-card"><div class="val" id="scPlayPct">{play_pct}%</div><div class="lbl">From Play</div></div>
<div class="summary-card"><div class="val" id="scFreePct">{free_pct}%</div><div class="lbl">From Frees</div></div>
<div class="summary-card"><div class="val" id="scAvgScorers">{scoring['avg_scorers_per_game']}</div><div class="lbl">Avg Scorers/Game</div></div>
</div>

<div class="pattern-grid" id="scoringInsights">
<div class="pattern-card pattern-blue">
<h3>⚽ Score Sources (by pts value)</h3>
<div class="insight" id="scSources">Goals: {scoring['total_goals']} ({scoring['total_goals']*3} pts — {goal_pts_pct}%)<br>
Points: {scoring['total_points']} ({scoring['total_points']} pts — {point_pts_pct}%)<br>
2-Pointers: {scoring['total_2pts']} ({scoring['total_2pts']*2} pts — {two_pts_pct}%)</div>
</div>
<div class="pattern-card pattern-green">
<h3>🎯 From Play vs Frees</h3>
<div class="insight" id="scPlayFrees">From play: {scoring['total_from_play']} scores ({play_pct}%)<br>
From frees: {scoring['total_from_frees']} scores ({free_pct}%)<br>
{len(scoring['players'])} different scorers used this season</div>
</div>
</div>

<div style="overflow-x:auto;margin-bottom:30px">
<table class="trends-table" id="scorersTable">
<thead><tr>
<th style="text-align:left">Player</th><th>Games</th><th>Total</th><th>Avg</th><th>Goals</th><th>Pts</th><th>2Pts</th><th>Play</th><th>Frees</th>
</tr></thead>
<tbody id="scorersBody">
{scorer_rows}
</tbody>
</table>
</div>

<hr style="border:none;border-top:2px solid #ecf0f1;margin:30px 0">

<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">📊 Shooting Efficiency</h2>

<div class="chart-box">
<div class="chart-title">🎯 Shot Accuracy vs Attack Efficiency</div>
<div style="text-align:center;margin-bottom:10px;font-size:.9em;color:#7f8c8d">🟢 Win · 🟡 Draw · 🔴 Loss — Top-right quadrant is the sweet spot</div>
<canvas id="scatterChart"></canvas>
</div>

<div class="chart-box">
<div class="chart-title">📊 Shot Accuracy by Game (Target: 70%)</div>
<canvas id="accChart"></canvas>
</div>

<div class="chart-box">
<div class="chart-title">⚡ Attack Efficiency by Game (Target: 75%)</div>
<canvas id="attEffChart"></canvas>
</div>

</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">📋 Game-by-Game Breakdown</h2>

<div style="text-align:center;margin-bottom:25px">
<span style="font-weight:bold;color:#2c3e50;margin-right:12px">Filter:</span>
<button class="comp-filter active" onclick="filterTable('All')">All</button>
<button class="comp-filter" onclick="filterTable('Spring League')">Spring League</button>
<button class="comp-filter" onclick="filterTable('Challenge')">Challenge</button>
<button class="comp-filter" onclick="filterTable('ACFL Div 3')">ACFL Div 3</button>
<button class="comp-filter" onclick="filterTable('ACFL Div 7')">ACFL Div 7</button>
</div>
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

new Chart(document.getElementById('scatterChart'),{{
type:'scatter',
data:{{datasets:[{{data:{scatter_data},backgroundColor:{scatter_colors},pointRadius:10,pointHoverRadius:13}}]}},
options:{{responsive:true,scales:{{x:{{title:{{display:true,text:'Attack Efficiency %'}},min:30,max:100}},y:{{title:{{display:true,text:'Shot Accuracy %'}},min:15,max:75}}}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.raw.label+' (Acc:'+ctx.raw.y+'%, Att:'+ctx.raw.x+'%)'}}}}}}}},
plugins:[{{
id:'quadrants',
afterDatasetsDraw(chart){{
const{{ctx,chartArea:{{left,right,top,bottom}},scales:{{x,y}}}}=chart;
const xPos=x.getPixelForValue(80);
const yPos=y.getPixelForValue(50);
ctx.save();
ctx.setLineDash([5,5]);
ctx.strokeStyle='rgba(0,0,0,0.2)';ctx.lineWidth=1;
ctx.beginPath();ctx.moveTo(xPos,top);ctx.lineTo(xPos,bottom);ctx.stroke();
ctx.beginPath();ctx.moveTo(left,yPos);ctx.lineTo(right,yPos);ctx.stroke();
ctx.fillStyle='rgba(46,204,113,0.08)';
ctx.fillRect(xPos,top,right-xPos,yPos-top);
ctx.fillStyle='rgba(46,204,113,0.5)';ctx.font='bold 11px Arial';ctx.textAlign='right';
ctx.fillText('SWEET SPOT',right-5,top+15);
ctx.restore();
}}
}}]
}});

new Chart(document.getElementById('accChart'),{{
type:'bar',
data:{{labels:labels,datasets:[{{label:'Accuracy %',data:{chart_acc},backgroundColor:{chart_bar_colors},borderColor:{chart_bar_borders},borderWidth:2}}]}},
options:{{responsive:true,scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}},plugins:{{legend:{{display:false}}}}}},
plugins:[{{
id:'accTargets',
afterDatasetsDraw(chart){{
const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=chart;
[{{val:70,label:'70% Target',color:'rgb(231,76,60)'}},{{val:50,label:'50% Floor',color:'rgb(243,156,18)'}}].forEach(t=>{{
const yPos=y.getPixelForValue(t.val);
ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle=t.color;ctx.lineWidth=2;
ctx.beginPath();ctx.moveTo(left,yPos);ctx.lineTo(right,yPos);ctx.stroke();
ctx.fillStyle=t.color;ctx.font='bold 10px Arial';ctx.textAlign='right';
ctx.fillText(t.label,right,yPos-4);ctx.restore();
}});
}}
}}]
}});

new Chart(document.getElementById('attEffChart'),{{
type:'bar',
data:{{labels:{chart_att_labels},datasets:[{{label:'Attack Efficiency %',data:{chart_att_eff},backgroundColor:{chart_att_colors},borderColor:{chart_att_borders},borderWidth:2}}]}},
options:{{responsive:true,scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}},plugins:{{legend:{{display:false}}}}}},
plugins:[{{
id:'attTargets',
afterDatasetsDraw(chart){{
const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=chart;
[{{val:80,label:'80% Sweet Spot',color:'rgb(46,204,113)'}},{{val:75,label:'75% Target',color:'rgb(231,76,60)'}}].forEach(t=>{{
const yPos=y.getPixelForValue(t.val);
ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle=t.color;ctx.lineWidth=2;
ctx.beginPath();ctx.moveTo(left,yPos);ctx.lineTo(right,yPos);ctx.stroke();
ctx.fillStyle=t.color;ctx.font='bold 10px Arial';ctx.textAlign='right';
ctx.fillText(t.label,right,yPos-4);ctx.restore();
}});
}}
}}]
}});

// Competition filter
const allComps={chart_comps};
const attComps={chart_att_comps};
const allLabels={chart_labels};
const allAcc={chart_acc};
const allBarColors={chart_bar_colors};
const allBarBorders={chart_bar_borders};
const allAttLabels={chart_att_labels};
const allAttEff={chart_att_eff};
const allAttColors={chart_att_colors};
const allAttBorders={chart_att_borders};
const allScatterData={scatter_data};
const allScatterColors={scatter_colors};

// Charts tab filter data
const allMargins={chart_margins};
const allMarginColors={chart_bar_colors};
const allMarginBorders={chart_bar_borders};
const allResults={chart_results};
const allKill2H={chart_k_2h};
const allOpp2H={chart_o_2h};
const allOurRuns={chart_k_runs};
const allOppRuns={chart_opp_runs};

function filterCharts(comp){{
  const btns=document.querySelectorAll('#charts .comp-filter');
  btns.forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  const marginChart=Chart.getChart('marginChart');
  const secChart=Chart.getChart('secondHalfChart');
  const runsChartObj=Chart.getChart('runsChart');
  if(comp==='All'){{
    marginChart.data.labels=allLabels;marginChart.data.datasets[0].data=allMargins;marginChart.data.datasets[0].backgroundColor=allMarginColors;marginChart.data.datasets[0].borderColor=allMarginBorders;
    secChart.data.labels=allLabels;secChart.data.datasets[0].data=allKill2H;secChart.data.datasets[1].data=allOpp2H;
    runsChartObj.data.labels=allLabels;runsChartObj.data.datasets[0].data=allOurRuns;runsChartObj.data.datasets[1].data=allOppRuns;
  }}else{{
    const fi=allComps.map((c,i)=>c===comp?i:-1).filter(i=>i>=0);
    marginChart.data.labels=fi.map(i=>allLabels[i]);marginChart.data.datasets[0].data=fi.map(i=>allMargins[i]);marginChart.data.datasets[0].backgroundColor=fi.map(i=>allMarginColors[i]);marginChart.data.datasets[0].borderColor=fi.map(i=>allMarginBorders[i]);
    secChart.data.labels=fi.map(i=>allLabels[i]);secChart.data.datasets[0].data=fi.map(i=>allKill2H[i]);secChart.data.datasets[1].data=fi.map(i=>allOpp2H[i]);
    runsChartObj.data.labels=fi.map(i=>allLabels[i]);runsChartObj.data.datasets[0].data=fi.map(i=>allOurRuns[i]);runsChartObj.data.datasets[1].data=fi.map(i=>allOppRuns[i]);
  }}
  marginChart.update();secChart.update();runsChartObj.update();
}}

function filterTable(comp){{
  const btns=document.querySelectorAll('#table .comp-filter');
  btns.forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  const rows=document.querySelectorAll('#trendsTable tbody tr');
  rows.forEach((row,i)=>{{
    if(comp==='All'){{row.style.display='';}}else{{row.style.display=allComps[i]===comp?'':'none';}}
  }});
}}

// Scoring filter data
const scoringCompData={scoring['comp_data_json']};

function filterAll(comp){{
  document.querySelectorAll('#shooting .comp-filter').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  filterScoring(comp);
  filterComp(comp);
}}

function filterScoring(comp){{
  const d=scoringCompData[comp];
  if(!d)return;
  const playPct=d.total_scores?Math.round(d.total_from_play/d.total_scores*100):0;
  const freePct=100-playPct;
  const goalPct=d.total_value?Math.round(d.total_goals*3/d.total_value*100):0;
  const pointPct=d.total_value?Math.round(d.total_points/d.total_value*100):0;
  const twoPct=d.total_value?Math.round(d.total_2pts*2/d.total_value*100):0;
  document.getElementById('scTotalVal').textContent=d.total_value;
  document.getElementById('scGoalsPts').textContent=d.total_goals+'-'+d.total_points;
  document.getElementById('sc2Pts').textContent=d.total_2pts;
  document.getElementById('scPlayPct').textContent=playPct+'%';
  document.getElementById('scFreePct').textContent=freePct+'%';
  document.getElementById('scAvgScorers').textContent=d.avg_scorers_per_game;
  document.getElementById('scSources').innerHTML='Goals: '+d.total_goals+' ('+(d.total_goals*3)+' pts \u2014 '+goalPct+'%)<br>Points: '+d.total_points+' ('+d.total_points+' pts \u2014 '+pointPct+'%)<br>2-Pointers: '+d.total_2pts+' ('+(d.total_2pts*2)+' pts \u2014 '+twoPct+'%)';
  document.getElementById('scPlayFrees').innerHTML='From play: '+d.total_from_play+' scores ('+playPct+'%)<br>From frees: '+d.total_from_frees+' scores ('+freePct+'%)<br>'+d.num_scorers+' different scorers'+(comp==='All'?' used this season':'');
  const tbody=document.getElementById('scorersBody');
  tbody.innerHTML='';
  d.players.forEach(p=>{{
    tbody.innerHTML+='<tr><td style="text-align:left;font-weight:bold">'+p.player+'</td><td>'+p.games+'</td><td style="font-weight:bold;color:#2a5298">'+p.total+'</td><td>'+p.avg+'</td><td>'+p.goals+'</td><td>'+p.points+'</td><td>'+p['2pts']+'</td><td>'+p.play+'</td><td>'+p.frees+'</td></tr>';
  }});
}}

function filterComp(comp){{
  const accChart=Chart.getChart('accChart');
  const attChart=Chart.getChart('attEffChart');
  const scChart=Chart.getChart('scatterChart');
  if(comp==='All'){{
    accChart.data.labels=allLabels;accChart.data.datasets[0].data=allAcc;accChart.data.datasets[0].backgroundColor=allBarColors;accChart.data.datasets[0].borderColor=allBarBorders;
    attChart.data.labels=allAttLabels;attChart.data.datasets[0].data=allAttEff;attChart.data.datasets[0].backgroundColor=allAttColors;attChart.data.datasets[0].borderColor=allAttBorders;
    scChart.data.datasets[0].data=allScatterData;scChart.data.datasets[0].backgroundColor=allScatterColors;
  }}else{{
    const fi=allComps.map((c,i)=>c===comp?i:-1).filter(i=>i>=0);
    accChart.data.labels=fi.map(i=>allLabels[i]);accChart.data.datasets[0].data=fi.map(i=>allAcc[i]);accChart.data.datasets[0].backgroundColor=fi.map(i=>allBarColors[i]);accChart.data.datasets[0].borderColor=fi.map(i=>allBarBorders[i]);
    const ai=attComps.map((c,i)=>c===comp?i:-1).filter(i=>i>=0);
    attChart.data.labels=ai.map(i=>allAttLabels[i]);attChart.data.datasets[0].data=ai.map(i=>allAttEff[i]);attChart.data.datasets[0].backgroundColor=ai.map(i=>allAttColors[i]);attChart.data.datasets[0].borderColor=ai.map(i=>allAttBorders[i]);
    scChart.data.datasets[0].data=ai.map(i=>allScatterData[i]);scChart.data.datasets[0].backgroundColor=ai.map(i=>allScatterColors[i]);
  }}
  accChart.update();attChart.update();scChart.update();
}}
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
