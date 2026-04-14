#!/usr/bin/env python3
"""
GPS Performance Report Generator
Reads GPS tracking CSV (STATSports format) and generates an HTML performance report.
Usage: python3 gps_generator.py <gps_csv_file>
"""

import csv
import sys
import json
from pathlib import Path


def read_gps_csv(filename):
    players = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Player Name']
            session_type = row['Session Type']
            if name not in players:
                players[name] = {}
            players[name][session_type] = {
                'total_distance': int(row['Total Distance']),
                'hsr': int(row['High Speed Running']),
                'dist_per_min': int(row['Distance per min']),
                'impacts': int(row['Impacts']),
                'max_speed': float(row['Max Speed']),
                'hid': int(row['High Intensity Distance']),
                'sprints': int(row['No of Sprints']),
                'sprint_distance': int(row['Sprint Distance']),
                'accelerations': int(row['Accelerations']),
                'decelerations': int(row['Decelerations']),
                'calories': int(row['Calories']),
                'hsr_per_min': int(row['HSR Per Min']),
                'hid_per_min': int(row['HID Per Min']),
                'sprint_dist_per_min': int(row['Sprint Distance Per Min']),
                'step_balance_l': int(row['Step Balance (L)']),
                'step_balance_r': int(row['Step Balance (R)']),
                'dsl': int(row['DSL']),
            }
    return players



def generate_html(csv_file):
    print(f"\n{'='*60}")
    print("GPS PERFORMANCE REPORT GENERATOR")
    print(f"{'='*60}\n")

    players = read_gps_csv(csv_file)
    print(f"📊 Found {len(players)} players")

    # Extract session info from first row
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        first = next(reader)
        session_name = first['Session Name']
        session_date = first['Session Date']
        club_name = first['Club Name']
        squad_name = first['Squad Name']

    # Build sorted lists for charts
    names = sorted(players.keys(), key=lambda n: players[n]['Total']['total_distance'], reverse=True)
    totals = [players[n]['Total'] for n in names]

    # Team averages
    num = len(names)
    avg = {k: round(sum(t[k] for t in totals) / num) for k in ['total_distance', 'hsr', 'hid', 'sprints', 'sprint_distance', 'impacts', 'calories', 'accelerations', 'decelerations']}
    avg['max_speed'] = round(max(t['max_speed'] for t in totals), 2)
    avg['dist_per_min'] = round(sum(t['dist_per_min'] for t in totals) / num)

    # Max values for bar scaling
    max_dist = max(t['total_distance'] for t in totals)
    max_hsr = max(t['hsr'] for t in totals) or 1
    max_hid = max(t['hid'] for t in totals) or 1
    max_sprints = max(t['sprints'] for t in totals) or 1
    max_sprint_dist = max(t['sprint_distance'] for t in totals) or 1
    max_impacts = max(t['impacts'] for t in totals) or 1

    # JSON data for charts
    chart_names = json.dumps(names)
    chart_dist = json.dumps([players[n]['Total']['total_distance'] for n in names])
    chart_hsr = json.dumps([players[n]['Total']['hsr'] for n in names])
    chart_hid = json.dumps([players[n]['Total']['hid'] for n in names])
    chart_sprints = json.dumps([players[n]['Total']['sprints'] for n in names])
    chart_max_speed = json.dumps([players[n]['Total']['max_speed'] for n in names])

    # Half-by-half data
    h1_dist = json.dumps([players[n].get('First Half', {}).get('total_distance', 0) for n in names])
    h2_dist = json.dumps([players[n].get('Second Half', {}).get('total_distance', 0) for n in names])
    h1_hsr = json.dumps([players[n].get('First Half', {}).get('hsr', 0) for n in names])
    h2_hsr = json.dumps([players[n].get('Second Half', {}).get('hsr', 0) for n in names])
    h1_sprints = json.dumps([players[n].get('First Half', {}).get('sprints', 0) for n in names])
    h2_sprints = json.dumps([players[n].get('Second Half', {}).get('sprints', 0) for n in names])

    # Half balance analysis helper
    def calc_half_balance(h1, h2):
        h1_hsr_pm = h1.get('hsr_per_min', 0)
        h2_hsr_pm = h2.get('hsr_per_min', 0)
        h1_hid_pm = h1.get('hid_per_min', 0)
        h2_hid_pm = h2.get('hid_per_min', 0)
        h1_sd_pm = h1.get('sprint_dist_per_min', 0)
        h2_sd_pm = h2.get('sprint_dist_per_min', 0)
        played_both = h1.get('total_distance', 0) > 0 and h2.get('total_distance', 0) > 0
        if not played_both:
            return {'label': 'SUB', 'color': '#95a5a6', 'icon': '🔄', 'value': '-', 'tip': 'Did not play both halves'}
        total_pm = h1_hsr_pm + h2_hsr_pm
        h1_pct = round(h1_hsr_pm / total_pm * 100) if total_pm > 0 else 50
        hsr_change = round((h2_hsr_pm - h1_hsr_pm) / h1_hsr_pm * 100) if h1_hsr_pm > 0 else 0
        hid_change = round((h2_hid_pm - h1_hid_pm) / h1_hid_pm * 100) if h1_hid_pm > 0 else 0
        sd_change = round((h2_sd_pm - h1_sd_pm) / h1_sd_pm * 100) if h1_sd_pm > 0 else 0
        composite = round(hsr_change * 0.4 + hid_change * 0.3 + sd_change * 0.3)
        tip = f'HSR/min:{h1_hsr_pm}→{h2_hsr_pm} | HID/min:{h1_hid_pm}→{h2_hid_pm} | Sprint/min:{h1_sd_pm}→{h2_sd_pm}'
        if composite <= -15:
            return {'label': '⚠️ Faded', 'color': '#e74c3c', 'icon': '🔻', 'value': f'{h1_pct}/{100-h1_pct}', 'tip': tip, 'composite': composite}
        elif composite <= -10:
            return {'label': 'Moderate fade', 'color': '#f39c12', 'icon': '🔸', 'value': f'{h1_pct}/{100-h1_pct}', 'tip': tip, 'composite': composite}
        elif composite >= 15:
            return {'label': 'Back-loaded', 'color': '#3498db', 'icon': '🔵', 'value': f'{h1_pct}/{100-h1_pct}', 'tip': tip, 'composite': composite}
        else:
            return {'label': '✅ Consistent', 'color': '#2ecc71', 'icon': '✅', 'value': f'{h1_pct}/{100-h1_pct}', 'tip': tip, 'composite': composite}

    # Player table rows
    table_rows = ''
    for name in names:
        t = players[name]['Total']
        h1 = players[name].get('First Half', {})
        h2 = players[name].get('Second Half', {})
        dist_pct = round(t['total_distance'] / max_dist * 100)
        bal = calc_half_balance(h1, h2)
        table_rows += f'''<tr>
<td><strong>{name}</strong></td>
<td>{t['total_distance']}m</td>
<td><div class="bar-mini"><div class="bar-fill-green" style="width:{dist_pct}%"></div></div></td>
<td>{t['hsr']}m</td>
<td>{t['hid']}m</td>
<td>{t['max_speed']}</td>
<td>{t['sprints']}</td>
<td>{t['sprint_distance']}m</td>
<td>{t['dist_per_min']}</td>
<td>{t['accelerations']}</td>
<td>{t['decelerations']}</td>
<td>{t['impacts']}</td>
<td style="color:{bal['color']};font-weight:bold" title="{bal['tip']}">{bal['label']}<br><span style="font-size:.75em;font-weight:normal">{bal['value']}</span></td>
</tr>
'''

    # Player cards for overview
    player_cards = ''
    # Rank badges
    dist_rank = sorted(names, key=lambda n: players[n]['Total']['total_distance'], reverse=True)
    hsr_rank = sorted(names, key=lambda n: players[n]['Total']['hsr'], reverse=True)
    speed_rank = sorted(names, key=lambda n: players[n]['Total']['max_speed'], reverse=True)
    sprint_rank = sorted(names, key=lambda n: players[n]['Total']['sprints'], reverse=True)

    for name in names:
        t = players[name]['Total']
        h1 = players[name].get('First Half', {})
        h2 = players[name].get('Second Half', {})
        h1d = h1.get('total_distance', 0)
        h2d = h2.get('total_distance', 0)
        h1_hsr_val = h1.get('hsr', 0)
        h2_hsr_val = h2.get('hsr', 0)
        h1_sprint_val = h1.get('sprint_distance', 0)
        h2_sprint_val = h2.get('sprint_distance', 0)
        bal = calc_half_balance(h1, h2)

        badges = []
        if dist_rank[0] == name:
            badges.append('🏃 Most Distance')
        if hsr_rank[0] == name:
            badges.append('⚡ Most HSR')
        if speed_rank[0] == name:
            badges.append('💨 Top Speed')
        if sprint_rank[0] == name:
            badges.append('🔥 Most Sprints')
        badge_html = ''.join(f'<span class="player-badge">{b}</span>' for b in badges)

        h1_sprints_n = h1.get('sprints', 0)
        h2_sprints_n = h2.get('sprints', 0)
        h1_avg_sprint = round(h1.get('sprint_distance', 0) / h1_sprints_n) if h1_sprints_n > 0 else 0
        h2_avg_sprint = round(h2.get('sprint_distance', 0) / h2_sprints_n) if h2_sprints_n > 0 else 0
        avg_sprint = round(t['sprint_distance'] / t['sprints']) if t['sprints'] > 0 else 0

        bar_max_dist = max(h1d, h2d) or 1
        bar_max_hsr = max(h1_hsr_val, h2_hsr_val) or 1
        bar_max_sd = max(h1_sprint_val, h2_sprint_val) or 1
        bar_max_sn = max(h1_sprints_n, h2_sprints_n) or 1

        player_cards += f'''<div class="player-card">
<div class="player-card-header">
<div class="player-card-name">{name}</div>
<div>{badge_html}</div>
</div>
<div class="player-card-grid">
<div class="metric"><div class="metric-value">{t['total_distance']}m</div><div class="metric-label">Total Distance</div></div>
<div class="metric"><div class="metric-value">{t['max_speed']} m/s</div><div class="metric-label">Max Speed</div></div>
<div class="metric"><div class="metric-value">{t['dist_per_min']}</div><div class="metric-label">Dist/min</div></div>
<div class="metric"><div class="metric-value">{t['impacts']}</div><div class="metric-label">Impacts</div></div>
<div class="metric"><div class="metric-value">{t['accelerations']}</div><div class="metric-label">Accelerations</div></div>
<div class="metric"><div class="metric-value">{t['decelerations']}</div><div class="metric-label">Decelerations</div></div>
<div class="metric"><div class="metric-value" style="color:{bal['color']}">{bal['label']}<br><span style="font-size:.7em;font-weight:normal">{bal['value']}</span></div><div class="metric-label">Half Balance</div></div>
</div>
<div class="half-compare">
<div class="half-section-label">Distance</div>
<div class="half-bar-row"><span class="half-label">1st</span><div class="half-bar"><div class="half-fill h1" style="width:{round(h1d/bar_max_dist*100)}%">{h1d}m</div></div></div>
<div class="half-bar-row"><span class="half-label">2nd</span><div class="half-bar"><div class="half-fill h2" style="width:{round(h2d/bar_max_dist*100)}%">{h2d}m</div></div></div>
<div class="half-section-label">High Speed Running</div>
<div class="half-bar-row"><span class="half-label">1st</span><div class="half-bar"><div class="half-fill h1" style="width:{round(h1_hsr_val/bar_max_hsr*100)}%">{h1_hsr_val}m</div></div></div>
<div class="half-bar-row"><span class="half-label">2nd</span><div class="half-bar"><div class="half-fill h2" style="width:{round(h2_hsr_val/bar_max_hsr*100)}%">{h2_hsr_val}m</div></div></div>
<div class="half-section-label">Sprint Distance</div>
<div class="half-bar-row"><span class="half-label">1st</span><div class="half-bar"><div class="half-fill h1" style="width:{round(h1_sprint_val/bar_max_sd*100)}%">{h1_sprint_val}m</div></div></div>
<div class="half-bar-row"><span class="half-label">2nd</span><div class="half-bar"><div class="half-fill h2" style="width:{round(h2_sprint_val/bar_max_sd*100)}%">{h2_sprint_val}m</div></div></div>
<div class="half-section-label">Sprints (count · avg length)</div>
<div class="half-bar-row"><span class="half-label">1st</span><div class="half-bar"><div class="half-fill h1" style="width:{round(h1_sprints_n/bar_max_sn*100)}%">{h1_sprints_n} · {h1_avg_sprint}m avg</div></div></div>
<div class="half-bar-row"><span class="half-label">2nd</span><div class="half-bar"><div class="half-fill h2" style="width:{round(h2_sprints_n/bar_max_sn*100)}%">{h2_sprints_n} · {h2_avg_sprint}m avg</div></div></div>
</div>
</div>
'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GPS Report — {session_name}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);color:#fff;padding:40px;text-align:center}}
.header h1{{font-size:2.8em;margin-bottom:8px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header p{{font-size:1.2em;opacity:.85}}
.meta-row{{display:flex;justify-content:center;gap:30px;margin-top:18px;font-size:1.05em;opacity:.9}}
.tabs{{display:flex;background:#34495e}}
.tab{{flex:1;padding:18px;text-align:center;color:#fff;cursor:pointer;transition:.3s;font-size:1.05em;font-weight:bold}}
.tab:hover{{background:#2c3e50}}
.tab.active{{background:#2a5298}}
.tab-content{{display:none;padding:35px}}
.tab-content.active{{display:block}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;margin-bottom:35px}}
.summary-card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:14px;padding:22px;text-align:center}}
.summary-card .val{{font-size:2.2em;font-weight:bold}}
.summary-card .lbl{{font-size:.85em;opacity:.85;margin-top:4px}}
.player-card{{background:#f8f9fa;border-radius:14px;padding:22px;margin-bottom:18px;border-left:5px solid #2a5298;transition:.2s}}
.player-card:hover{{box-shadow:0 4px 15px rgba(0,0,0,.1);transform:translateX(4px)}}
.player-card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}
.player-card-name{{font-size:1.35em;font-weight:bold;color:#2c3e50}}
.player-badge{{background:#2a5298;color:#fff;padding:3px 10px;border-radius:12px;font-size:.75em;margin-left:6px}}
.player-card-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:12px}}
.metric{{background:#fff;border-radius:8px;padding:10px;text-align:center}}
.metric-value{{font-size:1.3em;font-weight:bold;color:#2c3e50}}
.metric-label{{font-size:.72em;color:#7f8c8d;margin-top:2px}}
.half-compare{{margin-top:12px}}
.half-section-label{{font-size:.78em;font-weight:bold;color:#2a5298;margin:10px 0 4px;padding-left:68px}}
.half-section-label:first-child{{margin-top:0}}
.half-bar-row{{display:flex;align-items:center;margin-bottom:4px}}
.half-label{{min-width:65px;font-size:.82em;font-weight:bold;color:#555}}
.half-bar{{flex:1;height:22px;background:#ecf0f1;border-radius:6px;overflow:hidden}}
.half-fill{{height:100%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:.78em;font-weight:bold;min-width:40px}}
.half-fill.h1{{background:linear-gradient(90deg,#27ae60,#2ecc71)}}
.half-fill.h2{{background:linear-gradient(90deg,#2980b9,#3498db)}}
.chart-box{{background:#fff;border-radius:15px;padding:28px;margin:22px 0;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
.chart-title{{font-size:1.6em;color:#2c3e50;margin-bottom:18px;text-align:center;font-weight:bold}}
table.gps-table{{width:100%;border-collapse:collapse;margin:20px 0;font-size:.92em}}
.gps-table th{{background:#34495e;color:#fff;padding:12px 10px;text-align:left;cursor:pointer;user-select:none;white-space:nowrap}}
.gps-table th:hover{{background:#2c3e50}}
.gps-table td{{padding:10px;border-bottom:1px solid #ecf0f1}}
.gps-table tr:hover{{background:#f0f4ff}}
.gps-table tr:nth-child(even){{background:#f8f9fa}}
.bar-mini{{width:100%;height:14px;background:#ecf0f1;border-radius:7px;overflow:hidden}}
.bar-fill-green{{height:100%;background:linear-gradient(90deg,#27ae60,#2ecc71);border-radius:7px}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.9em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📡 GPS PERFORMANCE REPORT</h1>
<p>{session_name} — {club_name}</p>
<div class="meta-row">
<span>📅 {session_date}</span>
<span>👥 {squad_name}</span>
<span>🏃 {num} Players Tracked</span>
</div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('overview')">📊 Overview</div>
<div class="tab" onclick="showTab('players')">👤 Player Cards</div>
<div class="tab" onclick="showTab('charts')">📈 Charts</div>
<div class="tab" onclick="showTab('halves')">⏱️ Half Comparison</div>
<div class="tab" onclick="showTab('table')">📋 Full Table</div>
</div>

<div id="overview" class="tab-content active">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:22px;font-size:1.7em">⚡ Team Averages</h2>
<div class="summary-grid">
<div class="summary-card"><div class="val">{avg['total_distance']}m</div><div class="lbl">Avg Distance</div></div>
<div class="summary-card"><div class="val">{avg['hsr']}m</div><div class="lbl">Avg HSR</div></div>
<div class="summary-card"><div class="val">{avg['hid']}m</div><div class="lbl">Avg High Intensity</div></div>
<div class="summary-card"><div class="val">{avg['max_speed']} m/s</div><div class="lbl">Top Speed</div></div>
<div class="summary-card"><div class="val">{avg['sprints']}</div><div class="lbl">Avg Sprints</div></div>
<div class="summary-card"><div class="val">{avg['sprint_distance']}m</div><div class="lbl">Avg Sprint Dist</div></div>
<div class="summary-card"><div class="val">{avg['dist_per_min']}</div><div class="lbl">Avg Dist/min</div></div>
<div class="summary-card"><div class="val">{avg['impacts']}</div><div class="lbl">Avg Impacts</div></div>
<div class="summary-card"><div class="val">{avg['accelerations']}</div><div class="lbl">Avg Accels</div></div>
<div class="summary-card"><div class="val">{avg['decelerations']}</div><div class="lbl">Avg Decels</div></div>
</div>

<div class="chart-box">
<div class="chart-title">🏃 Total Distance by Player</div>
<canvas id="distChart"></canvas>
</div>

<div class="chart-box">
<div class="chart-title">💨 Max Speed by Player (m/s)</div>
<canvas id="speedChart"></canvas>
</div>
</div>

<div id="players" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:22px;font-size:1.7em">👤 Individual Player Reports</h2>
<div style="background:#f0f4ff;border:1px solid #c8d6f0;border-radius:12px;margin-bottom:25px;overflow:hidden">
<div onclick="this.parentElement.querySelector('.info-body').style.display=this.parentElement.querySelector('.info-body').style.display==='none'?'block':'none'" style="padding:14px 20px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-weight:bold;color:#2a5298;font-size:.95em">
<span>ℹ️ How to read Half Balance</span><span style="font-size:.8em">▾ tap to expand</span>
</div>
<div class="info-body" style="display:none;padding:0 20px 18px;font-size:.88em;color:#444;line-height:1.7">
<p style="margin-bottom:10px"><strong>Half Balance</strong> compares your <em>per-minute</em> intensity across both halves using three metrics:</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:12px;font-size:.95em">
<tr style="background:#e8eef8"><td style="padding:8px 12px;font-weight:bold">HSR per min</td><td style="padding:8px 12px;text-align:center;font-weight:bold">40%</td><td style="padding:8px 12px">High-speed running rate — most sensitive to fatigue</td></tr>
<tr><td style="padding:8px 12px;font-weight:bold">HID per min</td><td style="padding:8px 12px;text-align:center;font-weight:bold">30%</td><td style="padding:8px 12px">High-intensity distance rate — sustained hard efforts</td></tr>
<tr style="background:#e8eef8"><td style="padding:8px 12px;font-weight:bold">Sprint dist per min</td><td style="padding:8px 12px;text-align:center;font-weight:bold">30%</td><td style="padding:8px 12px">Sprint output rate — explosive capacity</td></tr>
</table>
<p style="margin-bottom:8px">Using per-minute rates means subs and uneven playing time are handled fairly. The split (e.g. 55/45) shows the 1st-half share vs 2nd-half share of HSR output.</p>
<p style="margin-bottom:8px"><strong>Categories:</strong></p>
<p style="margin-bottom:4px"><span style="color:#2ecc71;font-weight:bold">✅ Consistent</span> — Per-min intensity within 15% across halves. Ideal output.</p>
<p style="margin-bottom:4px"><span style="color:#f39c12;font-weight:bold">🔸 Moderate fade</span> — 10–15% per-min drop. Normal for most players.</p>
<p style="margin-bottom:4px"><span style="color:#e74c3c;font-weight:bold">⚠️ Faded</span> — &gt;15% per-min drop. Genuine fatigue flag for management.</p>
<p style="margin-bottom:4px"><span style="color:#3498db;font-weight:bold">🔵 Back-loaded</span> — Intensity <em>increased</em> &gt;15% in 2nd half. Not a concern — player was quieter early and ramped up.</p>
<p style="margin-bottom:8px"><span style="color:#95a5a6;font-weight:bold">🔄 SUB</span> — Did not play both halves. Excluded from comparison.</p>
<p style="color:#888;font-size:.9em">Hover over the value in the table for the per-minute breakdown.</p>
</div>
</div>
{player_cards}
</div>

<div id="charts" class="tab-content">
<div class="chart-box">
<div class="chart-title">⚡ High Speed Running by Player</div>
<canvas id="hsrChart"></canvas>
</div>
<div class="chart-box">
<div class="chart-title">🔥 High Intensity Distance by Player</div>
<canvas id="hidChart"></canvas>
</div>
<div class="chart-box">
<div class="chart-title">🏃‍♂️ Number of Sprints by Player</div>
<canvas id="sprintChart"></canvas>
</div>
</div>

<div id="halves" class="tab-content">
<div class="chart-box">
<div class="chart-title">⏱️ Distance — 1st Half vs 2nd Half</div>
<canvas id="halvesDistChart"></canvas>
</div>
<div class="chart-box">
<div class="chart-title">⚡ HSR — 1st Half vs 2nd Half</div>
<canvas id="halvesHsrChart"></canvas>
</div>
<div class="chart-box">
<div class="chart-title">🏃‍♂️ Sprints — 1st Half vs 2nd Half</div>
<canvas id="halvesSprintChart"></canvas>
</div>
</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">📋 Full GPS Data</h2>
<div style="overflow-x:auto">
<table class="gps-table" id="gpsTable">
<thead><tr>
<th>Player</th><th>Distance</th><th></th><th>HSR</th><th>HID</th><th>Max Spd</th><th>Sprints</th><th>Sprint Dist</th><th>Dist/min</th><th>Accels</th><th>Decels</th><th>Impacts</th><th>Half Balance</th>
</tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>
</div>
</div>
<div class="footer">{club_name} · GPS Performance Report · {session_date}</div>

<script>
function showTab(t){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active')}}

const names={chart_names};
const green='rgba(46,204,113,0.8)',greenBorder='rgba(39,174,96,1)';
const blue='rgba(52,152,219,0.8)',blueBorder='rgba(41,128,185,1)';
const purple='rgba(155,89,182,0.8)',purpleBorder='rgba(142,68,173,1)';
const orange='rgba(243,156,18,0.8)',orangeBorder='rgba(230,126,34,1)';

function hBar(id,data,label,bg,border){{
new Chart(document.getElementById(id),{{type:'bar',data:{{labels:names,datasets:[{{label:label,data:data,backgroundColor:bg,borderColor:border,borderWidth:2}}]}},options:{{indexAxis:'y',responsive:true,scales:{{x:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});
}}

hBar('distChart',{chart_dist},'Distance (m)',green,greenBorder);
hBar('hsrChart',{chart_hsr},'HSR (m)',orange,orangeBorder);
hBar('hidChart',{chart_hid},'HID (m)',purple,purpleBorder);
hBar('sprintChart',{chart_sprints},'Sprints',blue,blueBorder);

new Chart(document.getElementById('speedChart'),{{type:'bar',data:{{labels:names,datasets:[{{label:'Max Speed (m/s)',data:{chart_max_speed},backgroundColor:'rgba(231,76,60,0.8)',borderColor:'rgba(192,57,43,1)',borderWidth:2}}]}},options:{{indexAxis:'y',responsive:true,scales:{{x:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});

function halvesChart(id,h1,h2,label){{
new Chart(document.getElementById(id),{{type:'bar',data:{{labels:names,datasets:[{{label:'1st Half',data:h1,backgroundColor:green,borderColor:greenBorder,borderWidth:2}},{{label:'2nd Half',data:h2,backgroundColor:blue,borderColor:blueBorder,borderWidth:2}}]}},options:{{indexAxis:'y',responsive:true,scales:{{x:{{beginAtZero:true,stacked:false}}}},plugins:{{legend:{{display:true,position:'top'}}}}}}}});
}}

halvesChart('halvesDistChart',{h1_dist},{h2_dist},'Distance');
halvesChart('halvesHsrChart',{h1_hsr},{h2_hsr},'HSR');
halvesChart('halvesSprintChart',{h1_sprints},{h2_sprints},'Sprints');

// Table sorting
document.querySelectorAll('.gps-table th').forEach((th,i)=>{{
let asc=true;
th.addEventListener('click',()=>{{
const tbody=th.closest('table').querySelector('tbody');
const rows=Array.from(tbody.querySelectorAll('tr'));
rows.sort((a,b)=>{{
let av=a.children[i].textContent.replace(/[m%]/g,'').trim();
let bv=b.children[i].textContent.replace(/[m%]/g,'').trim();
if(!isNaN(av)&&!isNaN(bv))return asc?av-bv:bv-av;
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

    output_file = str(Path(csv_file).with_suffix('')) + '_GPS_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Generated: {output_file}")
    print(f"{'='*60}\n")
    return output_file


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 gps_generator.py <gps_csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)

    generate_html(csv_file)
