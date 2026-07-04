#!/usr/bin/env python3
"""Generate drought infographic split by competition."""

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
    score_events = ['Shot from play', 'Scoreable free']
    score_outcomes = ['Point', '2 Points', 'Goal']
    return (team == 'Killinkere' and name in score_events and outcome in score_outcomes)

def analyze_game(filepath):
    droughts = []
    scores = []
    try:
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        csv_lines = []
        for line in lines:
            if line.startswith('=') or line == '':
                break
            csv_lines.append(line)

        if not csv_lines:
            return [], []

        reader = csv.DictReader(csv_lines)
        game_end = 0

        for row in reader:
            time_str = row.get('Time', '')
            if not time_str:
                continue
            time_sec = parse_time(time_str)
            game_end = max(game_end, time_sec)
            if is_killinkere_score(row):
                scores.append(time_sec)

        if not scores:
            if game_end > 0:
                droughts.append({'start': 0, 'end': game_end, 'duration': game_end})
            return droughts, scores

        if scores[0] > 0:
            droughts.append({'start': 0, 'end': scores[0], 'duration': scores[0]})
        for i in range(len(scores) - 1):
            gap = scores[i+1] - scores[i]
            droughts.append({'start': scores[i], 'end': scores[i+1], 'duration': gap})
        if scores[-1] < game_end:
            droughts.append({'start': scores[-1], 'end': game_end, 'duration': game_end - scores[-1]})

    except Exception as e:
        return [], []

    return droughts, scores

def load_meta(filepath):
    meta = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    meta[key.strip()] = val.strip()
    return meta

def classify_competition(comp_str):
    """Group competitions into broader categories."""
    comp = comp_str.lower()
    if 'div 3' in comp or 'div3' in comp:
        return 'ACFL Div 3 (Senior)'
    elif 'div 7' in comp:
        return 'ACFL Div 7 (Reserve)'
    elif 'div 5' in comp:
        return 'ACFL Div 5 (Reserve)'
    elif 'spring league' in comp:
        return 'Ulster Spring League'
    elif 'challenge' in comp:
        return 'Challenge / Friendly'
    else:
        return comp_str

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir, 'Killinkere*.csv')))

    # Build game data with competition info
    comp_data = {}  # {competition: {'droughts': [], 'scores_by_game': [], 'games': []}}

    for filepath in csv_files:
        game_name = os.path.basename(filepath).replace('.csv', '')
        
        # Find matching meta file (handle spacing variations)
        meta_path = filepath.replace('.csv', '.meta')
        # Also try alternate spacing
        if not os.path.exists(meta_path):
            # Try finding meta with slightly different name
            base = os.path.basename(filepath).replace('.csv', '')
            possible_metas = glob.glob(os.path.join(data_dir, base.rstrip() + '*.meta'))
            if possible_metas:
                meta_path = possible_metas[0]
        
        meta = load_meta(meta_path)
        competition = classify_competition(meta.get('competition', 'Unknown'))
        
        droughts, scores = analyze_game(filepath)
        for d in droughts:
            d['game'] = game_name

        if competition not in comp_data:
            comp_data[competition] = {'droughts': [], 'scores_by_game': [], 'games': []}
        
        comp_data[competition]['droughts'].extend(droughts)
        comp_data[competition]['scores_by_game'].append((game_name, scores))
        comp_data[competition]['games'].append(game_name)

    # Sort competitions by number of games (most first)
    sorted_comps = sorted(comp_data.items(), key=lambda x: len(x[1]['games']), reverse=True)

    # Color palette for competitions
    comp_colors = {
        'ACFL Div 3 (Senior)': '#ff6b6b',
        'ACFL Div 7 (Reserve)': '#4ecdc4',
        'Ulster Spring League': '#ffa502',
        'Challenge / Friendly': '#a29bfe',
        'ACFL Div 5 (Reserve)': '#fd79a8',
    }

    # Create figure
    fig = plt.figure(figsize=(20, 26), facecolor='#1a1a2e')
    gs = GridSpec(5, 2, figure=fig, hspace=0.38, wspace=0.28,
                  left=0.06, right=0.94, top=0.93, bottom=0.03)

    title_color = '#ffffff'
    text_color = '#e0e0e0'
    accent_color = '#00d4aa'
    warning_color = '#ff6b6b'
    highlight_color = '#ffe66d'

    # Title
    fig.suptitle('KILLINKERE SCORING DROUGHTS — BY COMPETITION', fontsize=22, fontweight='bold',
                 color=title_color, y=0.97)
    comp_summary = '  |  '.join([f"{name}: {len(data['games'])} games" for name, data in sorted_comps])
    fig.text(0.5, 0.945, comp_summary, ha='center', fontsize=10, color=text_color, style='italic')

    # ============================================================
    # Panel 1: Droughts starting by phase — STACKED by competition
    # ============================================================
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#16213e')

    phases = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60']
    phase_ranges = [(0, 600), (600, 1200), (1200, 1800), (1800, 2400), (2400, 3000), (3000, 3600)]

    bottom = np.zeros(6)
    for comp_name, data in sorted_comps:
        sig = [d for d in data['droughts'] if d['duration'] >= 300]
        counts = []
        for start, end in phase_ranges:
            counts.append(sum(1 for d in sig if start <= d['start'] < end))
        color = comp_colors.get(comp_name, '#888888')
        ax1.bar(phases, counts, bottom=bottom, color=color, edgecolor='#ffffff',
                linewidth=0.3, width=0.7, label=comp_name)
        bottom += np.array(counts)

    ax1.set_title('Droughts (5+ min) by Phase & Competition', fontsize=12, fontweight='bold', color=title_color, pad=10)
    ax1.set_xlabel('Game Minute', fontsize=10, color=text_color)
    ax1.set_ylabel('Count', fontsize=10, color=text_color)
    ax1.tick_params(colors=text_color)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_color(text_color)
    ax1.spines['left'].set_color(text_color)
    ax1.legend(fontsize=7, loc='upper right', facecolor='#16213e', edgecolor=text_color, labelcolor=text_color)
    ax1.axvline(x=2.5, color='#ffffff', linestyle='--', alpha=0.3)
    ax1.text(1, bottom.max() + 1.5, '1ST HALF', ha='center', color=highlight_color, fontsize=9, fontweight='bold')
    ax1.text(4, bottom.max() + 1.5, '2ND HALF', ha='center', color=highlight_color, fontsize=9, fontweight='bold')

    # ============================================================
    # Panel 2: Avg drought duration by competition
    # ============================================================
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#16213e')

    comp_names = []
    avg_durations = []
    avg_sig_durations = []
    game_counts = []
    colors_list = []

    for comp_name, data in sorted_comps:
        all_d = [d['duration'] for d in data['droughts'] if d['duration'] > 0]
        sig_d = [d['duration'] for d in data['droughts'] if d['duration'] >= 300]
        comp_names.append(comp_name)
        avg_durations.append(np.mean(all_d) / 60 if all_d else 0)
        avg_sig_durations.append(np.mean(sig_d) / 60 if sig_d else 0)
        game_counts.append(len(data['games']))
        colors_list.append(comp_colors.get(comp_name, '#888888'))

    x = np.arange(len(comp_names))
    width = 0.35
    bars_all = ax2.bar(x - width/2, avg_durations, width, color=colors_list, alpha=0.5,
                        edgecolor='#ffffff', linewidth=0.3, label='All droughts')
    bars_sig = ax2.bar(x + width/2, avg_sig_durations, width, color=colors_list,
                        edgecolor='#ffffff', linewidth=0.5, label='Significant (5+ min)')

    ax2.set_title('Avg Drought Duration by Competition', fontsize=12, fontweight='bold', color=title_color, pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.replace(' (', '\n(') for n in comp_names], fontsize=8, color=text_color)
    ax2.set_ylabel('Minutes', fontsize=10, color=text_color)
    ax2.tick_params(colors=text_color)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_color(text_color)
    ax2.spines['left'].set_color(text_color)
    ax2.legend(fontsize=8, facecolor='#16213e', edgecolor=text_color, labelcolor=text_color)

    for bar, val in zip(bars_sig, avg_sig_durations):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                     f'{val:.1f}m', ha='center', va='bottom', color=title_color, fontsize=9)

    # ============================================================
    # Panel 3: Scoring timeline heatmap per competition
    # ============================================================
    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor('#16213e')

    for i, (comp_name, data) in enumerate(sorted_comps):
        minute_bins = np.zeros(65)
        for game_name, scores in data['scores_by_game']:
            for s in scores:
                minute = int(s / 60)
                if minute < 65:
                    minute_bins[minute] += 1
        # Normalize per game
        n_games = max(len(data['games']), 1)
        minute_bins_norm = minute_bins / n_games

        color = comp_colors.get(comp_name, '#888888')
        # Smooth with rolling average
        kernel = np.ones(3) / 3
        smoothed = np.convolve(minute_bins_norm, kernel, mode='same')
        ax3.plot(np.arange(65), smoothed, color=color, linewidth=2.5, label=f"{comp_name} ({n_games} games)", alpha=0.9)
        ax3.fill_between(np.arange(65), smoothed, alpha=0.1, color=color)

    ax3.set_title('Scoring Rate by Minute (per game, smoothed) — By Competition', fontsize=12,
                  fontweight='bold', color=title_color, pad=10)
    ax3.set_xlabel('Game Minute', fontsize=10, color=text_color)
    ax3.set_ylabel('Scores per Game', fontsize=10, color=text_color)
    ax3.tick_params(colors=text_color)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.spines['bottom'].set_color(text_color)
    ax3.spines['left'].set_color(text_color)
    ax3.axvline(x=30, color='#ffffff', linestyle='--', alpha=0.5, linewidth=1.5)
    ax3.text(30, ax3.get_ylim()[1] if ax3.get_ylim()[1] > 0 else 1, 'HT', ha='center',
             color=highlight_color, fontsize=10, fontweight='bold')
    ax3.axvspan(0, 5, alpha=0.08, color='red')
    ax3.axvspan(30, 35, alpha=0.08, color='red')
    ax3.legend(fontsize=9, loc='upper right', facecolor='#16213e', edgecolor=text_color, labelcolor=text_color)
    ax3.set_xlim(0, 63)

    # ============================================================
    # Panel 4: Per-competition phase heatmaps (small multiples)
    # ============================================================
    for idx, (comp_name, data) in enumerate(sorted_comps[:4]):
        row = 2 + idx // 2
        col = idx % 2
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor('#16213e')

        sig = [d for d in data['droughts'] if d['duration'] >= 300]
        n_games = len(data['games'])
        color = comp_colors.get(comp_name, '#888888')

        # Drought starts per phase
        counts = []
        for start, end in phase_ranges:
            counts.append(sum(1 for d in sig if start <= d['start'] < end))

        # Also show avg duration per phase
        avg_dur_phase = []
        for start, end in phase_ranges:
            phase_d = [d['duration'] for d in data['droughts'] if start <= d['start'] < end and d['duration'] > 0]
            avg_dur_phase.append(np.mean(phase_d) / 60 if phase_d else 0)

        # Dual axis
        bars = ax.bar(phases, counts, color=color, alpha=0.7, edgecolor='#ffffff', linewidth=0.3, width=0.6)
        ax.set_ylabel('Drought Count (5+ min)', fontsize=9, color=text_color)

        ax2_twin = ax.twinx()
        ax2_twin.plot(phases, avg_dur_phase, color=highlight_color, linewidth=2.5, marker='o', markersize=6)
        ax2_twin.set_ylabel('Avg Duration (min)', fontsize=9, color=highlight_color)
        ax2_twin.tick_params(colors=highlight_color)
        ax2_twin.spines['right'].set_color(highlight_color)
        ax2_twin.spines['top'].set_visible(False)

        ax.set_title(f'{comp_name} ({n_games} games)', fontsize=11, fontweight='bold', color=color, pad=8)
        ax.tick_params(colors=text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.axvline(x=2.5, color='#ffffff', linestyle='--', alpha=0.3)

        # Annotate max drought
        if sig:
            longest = max(sig, key=lambda d: d['duration'])
            ax.text(0.02, 0.95, f'Longest: {format_time(longest["duration"])}',
                    transform=ax.transAxes, fontsize=8, color=warning_color, va='top',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#0f3460', edgecolor=warning_color, alpha=0.8))

        # Annotate opening score avg
        opening = [d['duration'] for d in data['droughts'] if d['start'] == 0]
        if opening:
            avg_open = np.mean(opening) / 60
            ax.text(0.98, 0.95, f'Avg 1st score: {avg_open:.1f} min',
                    transform=ax.transAxes, fontsize=8, color=accent_color, va='top', ha='right',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#0f3460', edgecolor=accent_color, alpha=0.8))

    # ============================================================
    # Panel 5: If there's a 5th competition, or summary stats
    # ============================================================
    if len(sorted_comps) >= 5:
        ax_last = fig.add_subplot(gs[4, :])
    else:
        ax_last = fig.add_subplot(gs[4, :])
    
    ax_last.set_facecolor('#0f3460')
    ax_last.set_xlim(0, 10)
    ax_last.set_ylim(0, 10)
    ax_last.axis('off')

    ax_last.text(5, 9.3, 'COMPETITION COMPARISON — KEY FINDINGS', ha='center', fontsize=14,
                 fontweight='bold', color=highlight_color)

    # Calculate comparison stats
    findings = []
    for comp_name, data in sorted_comps:
        sig = [d for d in data['droughts'] if d['duration'] >= 300]
        n_games = len(data['games'])
        droughts_per_game = len(sig) / max(n_games, 1)
        avg_sig = np.mean([d['duration'] for d in sig]) / 60 if sig else 0
        opening = [d['duration'] for d in data['droughts'] if d['start'] == 0]
        avg_open = np.mean(opening) / 60 if opening else 0
        findings.append({
            'name': comp_name,
            'dpg': droughts_per_game,
            'avg': avg_sig,
            'open': avg_open,
            'games': n_games
        })

    # Sort by droughts per game
    findings.sort(key=lambda x: x['dpg'], reverse=True)

    # Header
    ax_last.text(0.3, 7.8, 'Competition', fontsize=10, fontweight='bold', color=title_color, va='center')
    ax_last.text(4.0, 7.8, 'Games', fontsize=10, fontweight='bold', color=title_color, va='center', ha='center')
    ax_last.text(5.3, 7.8, 'Droughts/Game', fontsize=10, fontweight='bold', color=title_color, va='center', ha='center')
    ax_last.text(6.9, 7.8, 'Avg Duration', fontsize=10, fontweight='bold', color=title_color, va='center', ha='center')
    ax_last.text(8.5, 7.8, 'Avg 1st Score', fontsize=10, fontweight='bold', color=title_color, va='center', ha='center')

    ax_last.plot([0.2, 9.8], [7.4, 7.4], color=text_color, linewidth=0.5, alpha=0.5)

    for i, f in enumerate(findings):
        y = 6.5 - i * 1.2
        color = comp_colors.get(f['name'], '#888888')
        ax_last.plot([0.15, 0.25], [y, y], color=color, linewidth=4, solid_capstyle='round')
        ax_last.text(0.4, y, f['name'], fontsize=10, color=color, va='center', fontweight='bold')
        ax_last.text(4.0, y, str(f['games']), fontsize=10, color=text_color, va='center', ha='center')
        
        # Color code droughts/game
        dpg_color = warning_color if f['dpg'] >= 4.5 else '#ffa502' if f['dpg'] >= 4 else accent_color
        ax_last.text(5.3, y, f"{f['dpg']:.1f}", fontsize=11, color=dpg_color, va='center', ha='center', fontweight='bold')
        
        avg_color = warning_color if f['avg'] >= 10 else '#ffa502' if f['avg'] >= 8.5 else accent_color
        ax_last.text(6.9, y, f"{f['avg']:.1f} min", fontsize=10, color=avg_color, va='center', ha='center')
        
        open_color = warning_color if f['open'] >= 5 else '#ffa502' if f['open'] >= 3.5 else accent_color
        ax_last.text(8.5, y, f"{f['open']:.1f} min", fontsize=10, color=open_color, va='center', ha='center')

    # Bottom insight
    worst_comp = findings[0]
    best_comp = findings[-1]
    ax_last.text(5, 0.5,
                 f"Worst drought rate: {worst_comp['name']} ({worst_comp['dpg']:.1f}/game)   |   "
                 f"Best: {best_comp['name']} ({best_comp['dpg']:.1f}/game)",
                 ha='center', fontsize=10, color=text_color, style='italic')

    output_path = os.path.join(data_dir, 'killinkere_drought_by_competition.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Infographic saved to: {output_path}")

if __name__ == '__main__':
    main()
