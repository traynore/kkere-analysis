#!/usr/bin/env python3
"""Generate drought infographic comparing Div 3 vs Div 7 only."""

import csv
import os
import glob
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np

def parse_time(time_str):
    parts = time_str.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def is_killinkere_score(row):
    team = row.get('Team Name', '')
    name = row.get('Name', '')
    outcome = row.get('Outcome', '')
    return (team == 'Killinkere' and
            name in ['Shot from play', 'Scoreable free'] and
            outcome in ['Point', '2 Points', 'Goal'])

def analyze_game(filepath):
    droughts, scores = [], []
    try:
        for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        csv_lines = [l for l in lines if l and not l.startswith('=')]
        # Stop at blank or separator
        clean = []
        for l in lines:
            if l.strip() == '' or l.startswith('='):
                break
            clean.append(l)
        if not clean:
            return [], []

        reader = csv.DictReader(clean)
        game_end = 0
        for row in reader:
            time_str = row.get('Time', '')
            if not time_str:
                continue
            t = parse_time(time_str)
            game_end = max(game_end, t)
            if is_killinkere_score(row):
                scores.append(t)

        if not scores:
            if game_end > 0:
                droughts.append({'start': 0, 'end': game_end, 'duration': game_end})
            return droughts, scores

        if scores[0] > 0:
            droughts.append({'start': 0, 'end': scores[0], 'duration': scores[0]})
        for i in range(len(scores) - 1):
            droughts.append({'start': scores[i], 'end': scores[i+1], 'duration': scores[i+1] - scores[i]})
        if scores[-1] < game_end:
            droughts.append({'start': scores[-1], 'end': game_end, 'duration': game_end - scores[-1]})
    except:
        pass
    return droughts, scores

def load_meta(filepath):
    meta = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    meta[k.strip()] = v.strip()
    return meta

def classify(comp_str):
    comp = comp_str.lower()
    if 'div 3' in comp or 'div3' in comp:
        return 'Div 3'
    elif 'div 7' in comp:
        return 'Div 7'
    return None

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir, 'Killinkere*.csv')))

    comp_data = {'Div 3': {'droughts': [], 'scores': [], 'games': []},
                 'Div 7': {'droughts': [], 'scores': [], 'games': []}}

    for filepath in csv_files:
        game_name = os.path.basename(filepath).replace('.csv', '')
        meta = load_meta(filepath.replace('.csv', '.meta'))
        comp = classify(meta.get('competition', ''))
        if comp is None:
            continue

        droughts, scores = analyze_game(filepath)
        for d in droughts:
            d['game'] = game_name
        comp_data[comp]['droughts'].extend(droughts)
        comp_data[comp]['scores'].append((game_name, scores))
        comp_data[comp]['games'].append(game_name)

    div3 = comp_data['Div 3']
    div7 = comp_data['Div 7']

    c3 = '#ff6b6b'
    c7 = '#4ecdc4'

    # Figure
    fig = plt.figure(figsize=(18, 20), facecolor='#1a1a2e')
    gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3,
                  left=0.07, right=0.93, top=0.91, bottom=0.04)

    tc = '#ffffff'
    tx = '#e0e0e0'
    hl = '#ffe66d'

    fig.suptitle('KILLINKERE SCORING DROUGHTS — DIV 3 vs DIV 7', fontsize=22,
                 fontweight='bold', color=tc, y=0.96)
    fig.text(0.5, 0.93,
             f'Div 3: {len(div3["games"])} games (Senior)   |   Div 7: {len(div7["games"])} games (Reserve)',
             ha='center', fontsize=12, color=tx)

    phases = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60']
    phase_ranges = [(0, 600), (600, 1200), (1200, 1800), (1800, 2400), (2400, 3000), (3000, 3600)]

    # ============================================================
    # Panel 1: Drought count by phase — side by side
    # ============================================================
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#16213e')

    x = np.arange(6)
    w = 0.35
    sig3 = [d for d in div3['droughts'] if d['duration'] >= 300]
    sig7 = [d for d in div7['droughts'] if d['duration'] >= 300]
    counts3 = [sum(1 for d in sig3 if s <= d['start'] < e) for s, e in phase_ranges]
    counts7 = [sum(1 for d in sig7 if s <= d['start'] < e) for s, e in phase_ranges]

    # Normalize per game
    n3 = max(len(div3['games']), 1)
    n7 = max(len(div7['games']), 1)
    norm3 = [c / n3 for c in counts3]
    norm7 = [c / n7 for c in counts7]

    ax1.bar(x - w/2, norm3, w, color=c3, edgecolor='#fff', linewidth=0.3, label='Div 3')
    ax1.bar(x + w/2, norm7, w, color=c7, edgecolor='#fff', linewidth=0.3, label='Div 7')

    ax1.set_title('Droughts per Game by Phase', fontsize=12, fontweight='bold', color=tc, pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(phases)
    ax1.set_xlabel('Game Minute', fontsize=10, color=tx)
    ax1.set_ylabel('Droughts per Game (5+ min)', fontsize=10, color=tx)
    ax1.tick_params(colors=tx)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_color(tx)
    ax1.spines['left'].set_color(tx)
    ax1.legend(fontsize=10, facecolor='#16213e', edgecolor=tx, labelcolor=tx)
    ax1.axvline(x=2.5, color='#fff', linestyle='--', alpha=0.3)

    # ============================================================
    # Panel 2: Avg drought duration by phase
    # ============================================================
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#16213e')

    avg3 = []
    avg7 = []
    for s, e in phase_ranges:
        d3 = [d['duration'] for d in div3['droughts'] if s <= d['start'] < e and d['duration'] > 0]
        d7 = [d['duration'] for d in div7['droughts'] if s <= d['start'] < e and d['duration'] > 0]
        avg3.append(np.mean(d3) / 60 if d3 else 0)
        avg7.append(np.mean(d7) / 60 if d7 else 0)

    ax2.plot(phases, avg3, color=c3, linewidth=3, marker='o', markersize=8, label='Div 3')
    ax2.plot(phases, avg7, color=c7, linewidth=3, marker='s', markersize=8, label='Div 7')
    ax2.fill_between(phases, avg3, alpha=0.1, color=c3)
    ax2.fill_between(phases, avg7, alpha=0.1, color=c7)

    ax2.set_title('Avg Drought Duration by Phase', fontsize=12, fontweight='bold', color=tc, pad=10)
    ax2.set_xlabel('Game Minute', fontsize=10, color=tx)
    ax2.set_ylabel('Minutes', fontsize=10, color=tx)
    ax2.tick_params(colors=tx)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_color(tx)
    ax2.spines['left'].set_color(tx)
    ax2.legend(fontsize=10, facecolor='#16213e', edgecolor=tx, labelcolor=tx)
    ax2.axvline(x=2.5, color='#fff', linestyle='--', alpha=0.3)
    ax2.axhline(y=5, color=hl, linestyle=':', alpha=0.4)
    ax2.text(5.3, 5.1, '5 min', color=hl, fontsize=8)

    # ============================================================
    # Panel 3: Scoring timeline comparison (full width)
    # ============================================================
    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor('#16213e')

    for comp_name, data, color in [('Div 3', div3, c3), ('Div 7', div7, c7)]:
        minute_bins = np.zeros(65)
        for _, scores in data['scores']:
            for s in scores:
                m = int(s / 60)
                if m < 65:
                    minute_bins[m] += 1
        ng = max(len(data['games']), 1)
        normed = minute_bins / ng
        kernel = np.ones(3) / 3
        smoothed = np.convolve(normed, kernel, mode='same')
        ax3.plot(np.arange(65), smoothed, color=color, linewidth=2.5, label=f'{comp_name} ({ng} games)')
        ax3.fill_between(np.arange(65), smoothed, alpha=0.15, color=color)

    ax3.set_title('Scoring Rate per Minute (normalised per game)', fontsize=12,
                  fontweight='bold', color=tc, pad=10)
    ax3.set_xlabel('Game Minute', fontsize=10, color=tx)
    ax3.set_ylabel('Scores per Game', fontsize=10, color=tx)
    ax3.tick_params(colors=tx)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.spines['bottom'].set_color(tx)
    ax3.spines['left'].set_color(tx)
    ax3.axvline(x=30, color='#fff', linestyle='--', alpha=0.5, linewidth=1.5)
    ax3.text(30, ax3.get_ylim()[1] * 0.95 if ax3.get_ylim()[1] > 0 else 0.5, 'HALF TIME',
             ha='center', color=hl, fontsize=10, fontweight='bold')
    ax3.axvspan(0, 5, alpha=0.08, color='red')
    ax3.axvspan(30, 35, alpha=0.08, color='red')
    ax3.legend(fontsize=11, loc='upper right', facecolor='#16213e', edgecolor=tx, labelcolor=tx)
    ax3.set_xlim(0, 63)

    # ============================================================
    # Panel 4: Top droughts per competition (side by side)
    # ============================================================
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.set_facecolor('#16213e')
    top3 = sorted(sig3, key=lambda d: d['duration'], reverse=True)[:8]
    y_pos = np.arange(len(top3))
    labels3 = [d['game'].replace('Killinkere ', '')[:28] for d in top3]
    ax4.barh(y_pos, [d['duration']/60 for d in top3], color=c3, edgecolor='#fff', linewidth=0.3, height=0.7)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(labels3, fontsize=8, color=tx)
    ax4.set_xlabel('Minutes', fontsize=10, color=tx)
    ax4.set_title('Longest Droughts — Div 3', fontsize=12, fontweight='bold', color=c3, pad=10)
    ax4.tick_params(colors=tx)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    ax4.spines['bottom'].set_color(tx)
    ax4.spines['left'].set_color(tx)
    ax4.invert_yaxis()
    for i, d in enumerate(top3):
        ax4.text(d['duration']/60 + 0.2, i, f"{format_time(d['duration'])} (min {d['start']//60}-{d['end']//60})",
                 va='center', color=tx, fontsize=8)

    ax5 = fig.add_subplot(gs[2, 1])
    ax5.set_facecolor('#16213e')
    top7 = sorted(sig7, key=lambda d: d['duration'], reverse=True)[:8]
    y_pos = np.arange(len(top7))
    labels7 = [d['game'].replace('Killinkere ', '')[:28] for d in top7]
    ax5.barh(y_pos, [d['duration']/60 for d in top7], color=c7, edgecolor='#fff', linewidth=0.3, height=0.7)
    ax5.set_yticks(y_pos)
    ax5.set_yticklabels(labels7, fontsize=8, color=tx)
    ax5.set_xlabel('Minutes', fontsize=10, color=tx)
    ax5.set_title('Longest Droughts — Div 7', fontsize=12, fontweight='bold', color=c7, pad=10)
    ax5.tick_params(colors=tx)
    ax5.spines['top'].set_visible(False)
    ax5.spines['right'].set_visible(False)
    ax5.spines['bottom'].set_color(tx)
    ax5.spines['left'].set_color(tx)
    ax5.invert_yaxis()
    for i, d in enumerate(top7):
        ax5.text(d['duration']/60 + 0.2, i, f"{format_time(d['duration'])} (min {d['start']//60}-{d['end']//60})",
                 va='center', color=tx, fontsize=8)

    # ============================================================
    # Panel 5: Summary comparison
    # ============================================================
    ax6 = fig.add_subplot(gs[3, :])
    ax6.set_facecolor('#0f3460')
    ax6.set_xlim(0, 10)
    ax6.set_ylim(0, 10)
    ax6.axis('off')

    ax6.text(5, 9.3, 'HEAD-TO-HEAD COMPARISON', ha='center', fontsize=14,
             fontweight='bold', color=hl)

    # Stats
    def comp_stats(data, sig):
        n = max(len(data['games']), 1)
        opening = [d['duration'] for d in data['droughts'] if d['start'] == 0]
        return {
            'games': n,
            'dpg': len(sig) / n,
            'avg_sig': np.mean([d['duration'] for d in sig]) / 60 if sig else 0,
            'longest': max(d['duration'] for d in sig) / 60 if sig else 0,
            'avg_open': np.mean(opening) / 60 if opening else 0,
            'h1_droughts': sum(1 for d in sig if d['start'] < 1800) / n,
            'h2_droughts': sum(1 for d in sig if d['start'] >= 1800) / n,
        }

    s3 = comp_stats(div3, sig3)
    s7 = comp_stats(div7, sig7)

    metrics = [
        ('Droughts per Game (5+ min)', f"{s3['dpg']:.1f}", f"{s7['dpg']:.1f}"),
        ('Avg Drought Duration', f"{s3['avg_sig']:.1f} min", f"{s7['avg_sig']:.1f} min"),
        ('Longest Single Drought', f"{s3['longest']:.1f} min", f"{s7['longest']:.1f} min"),
        ('Avg Time to 1st Score', f"{s3['avg_open']:.1f} min", f"{s7['avg_open']:.1f} min"),
        ('1st Half Droughts/Game', f"{s3['h1_droughts']:.1f}", f"{s7['h1_droughts']:.1f}"),
        ('2nd Half Droughts/Game', f"{s3['h2_droughts']:.1f}", f"{s7['h2_droughts']:.1f}"),
    ]

    # Column headers
    ax6.text(3.5, 7.8, 'Metric', fontsize=11, fontweight='bold', color=tc, va='center')
    ax6.text(6.5, 7.8, 'Div 3', fontsize=11, fontweight='bold', color=c3, va='center', ha='center')
    ax6.text(8.5, 7.8, 'Div 7', fontsize=11, fontweight='bold', color=c7, va='center', ha='center')
    ax6.plot([2.0, 9.5], [7.4, 7.4], color=tx, linewidth=0.5, alpha=0.5)

    for i, (label, v3, v7) in enumerate(metrics):
        y = 6.5 - i * 1.1
        ax6.text(3.5, y, label, fontsize=10, color=tx, va='center')
        ax6.text(6.5, y, v3, fontsize=11, color=c3, va='center', ha='center', fontweight='bold')
        ax6.text(8.5, y, v7, fontsize=11, color=c7, va='center', ha='center', fontweight='bold')

    # Verdict
    if s3['dpg'] > s7['dpg']:
        verdict = "Div 3 has MORE frequent droughts -- higher-level opposition restricts scoring opportunities"
    else:
        verdict = "Div 7 has MORE frequent droughts -- possibly less clinical finishing at reserve level"
    ax6.text(5, 0.4, verdict, ha='center', fontsize=10, color=hl, style='italic')

    output_path = os.path.join(data_dir, 'killinkere_drought_div3_vs_div7.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")

if __name__ == '__main__':
    main()
