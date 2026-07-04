#!/usr/bin/env python3
"""Generate a visual infographic of Killinkere scoring drought patterns."""

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
        scores = []
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

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir, 'Killinkere*.csv')))

    all_droughts = []
    all_scores_by_game = []
    game_names = []

    for filepath in csv_files:
        game_name = os.path.basename(filepath).replace('.csv', '').replace('Killinkere ', '')
        droughts, scores = analyze_game(filepath)
        for d in droughts:
            d['game'] = game_name
        all_droughts.extend(droughts)
        all_scores_by_game.append((game_name, scores))
        game_names.append(game_name)

    sig_droughts = [d for d in all_droughts if d['duration'] >= 300]

    # Set up the figure
    fig = plt.figure(figsize=(18, 22), facecolor='#1a1a2e')
    gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3,
                  left=0.06, right=0.94, top=0.92, bottom=0.04)

    title_color = '#ffffff'
    text_color = '#e0e0e0'
    accent_color = '#00d4aa'
    warning_color = '#ff6b6b'
    bar_color = '#4ecdc4'
    highlight_color = '#ffe66d'

    # Title
    fig.suptitle('KILLINKERE SCORING DROUGHT ANALYSIS', fontsize=24, fontweight='bold',
                 color=title_color, y=0.97)
    fig.text(0.5, 0.94, f'23 Games Analyzed  •  98 Significant Droughts (5+ min)  •  Longest: 21:44',
             ha='center', fontsize=12, color=text_color, style='italic')

    # 1. Heatmap - When droughts START (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#16213e')
    phases = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60']
    phase_ranges = [(0, 600), (600, 1200), (1200, 1800), (1800, 2400), (2400, 3000), (3000, 3600)]
    drought_counts = []
    for start, end in phase_ranges:
        count = sum(1 for d in sig_droughts if start <= d['start'] < end)
        drought_counts.append(count)

    colors = []
    for c in drought_counts:
        if c >= 25:
            colors.append('#ff0000')
        elif c >= 18:
            colors.append('#ff6b6b')
        elif c >= 14:
            colors.append('#ffa502')
        else:
            colors.append('#4ecdc4')

    bars = ax1.bar(phases, drought_counts, color=colors, edgecolor='#ffffff', linewidth=0.5, width=0.7)
    ax1.set_title('Droughts Starting by Game Phase', fontsize=13, fontweight='bold', color=title_color, pad=10)
    ax1.set_xlabel('Game Minute', fontsize=10, color=text_color)
    ax1.set_ylabel('Number of Droughts (5+ min)', fontsize=10, color=text_color)
    ax1.tick_params(colors=text_color)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_color(text_color)
    ax1.spines['left'].set_color(text_color)
    for bar, count in zip(bars, drought_counts):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                 str(count), ha='center', va='bottom', color=title_color, fontweight='bold', fontsize=11)

    # Add half labels
    ax1.axvline(x=2.5, color='#ffffff', linestyle='--', alpha=0.4, linewidth=1)
    ax1.text(1, max(drought_counts) + 3, '1ST HALF', ha='center', color=highlight_color, fontsize=10, fontweight='bold')
    ax1.text(4, max(drought_counts) + 3, '2ND HALF', ha='center', color=highlight_color, fontsize=10, fontweight='bold')

    # 2. Average drought duration by phase (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#16213e')
    avg_durations = []
    for start, end in phase_ranges:
        phase_droughts = [d for d in all_droughts if start <= d['start'] < end and d['duration'] > 0]
        if phase_droughts:
            avg = sum(d['duration'] for d in phase_droughts) / len(phase_droughts)
        else:
            avg = 0
        avg_durations.append(avg / 60)  # Convert to minutes

    colors2 = ['#ff6b6b' if v >= 4.7 else '#ffa502' if v >= 4.3 else '#4ecdc4' for v in avg_durations]
    bars2 = ax2.bar(phases, avg_durations, color=colors2, edgecolor='#ffffff', linewidth=0.5, width=0.7)
    ax2.set_title('Average Drought Duration by Phase', fontsize=13, fontweight='bold', color=title_color, pad=10)
    ax2.set_xlabel('Game Minute', fontsize=10, color=text_color)
    ax2.set_ylabel('Avg Duration (minutes)', fontsize=10, color=text_color)
    ax2.tick_params(colors=text_color)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_color(text_color)
    ax2.spines['left'].set_color(text_color)
    ax2.axhline(y=5, color=warning_color, linestyle='--', alpha=0.5, linewidth=1)
    ax2.text(5.4, 5.05, '5 min', color=warning_color, fontsize=8, va='bottom')
    for bar, val in zip(bars2, avg_durations):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
                 f'{val:.1f}m', ha='center', va='bottom', color=title_color, fontsize=10)
    ax2.axvline(x=2.5, color='#ffffff', linestyle='--', alpha=0.4, linewidth=1)

    # 3. Timeline heatmap - all scores across games (middle left)
    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor('#16213e')

    # Create a heatmap of scoring activity per minute
    minute_bins = np.zeros(65)
    for game_name, scores in all_scores_by_game:
        for s in scores:
            minute = int(s / 60)
            if minute < 65:
                minute_bins[minute] += 1

    # Normalize and plot as bar chart
    x = np.arange(65)
    max_scores = max(minute_bins) if max(minute_bins) > 0 else 1
    colors3 = []
    for val in minute_bins:
        ratio = val / max_scores
        if ratio < 0.25:
            colors3.append('#ff0000')
        elif ratio < 0.4:
            colors3.append('#ff6b6b')
        elif ratio < 0.6:
            colors3.append('#ffa502')
        else:
            colors3.append('#00d4aa')

    ax3.bar(x, minute_bins, color=colors3, width=1.0, edgecolor='none')
    ax3.set_title('Scoring Frequency by Game Minute (All 23 Games)', fontsize=13, fontweight='bold', color=title_color, pad=10)
    ax3.set_xlabel('Game Minute', fontsize=10, color=text_color)
    ax3.set_ylabel('Total Scores', fontsize=10, color=text_color)
    ax3.tick_params(colors=text_color)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.spines['bottom'].set_color(text_color)
    ax3.spines['left'].set_color(text_color)
    ax3.axvline(x=30, color='#ffffff', linestyle='--', alpha=0.6, linewidth=1.5)
    ax3.text(30, max(minute_bins) + 0.5, 'HALF TIME', ha='center', color=highlight_color, fontsize=10, fontweight='bold')

    # Add danger zones
    ax3.axvspan(0, 5, alpha=0.15, color='red')
    ax3.axvspan(30, 35, alpha=0.15, color='red')
    ax3.text(2.5, max(minute_bins) * 0.85, 'SLOW\nSTART', ha='center', color=warning_color, fontsize=9, fontweight='bold')
    ax3.text(32.5, max(minute_bins) * 0.85, 'POST\nBREAK', ha='center', color=warning_color, fontsize=9, fontweight='bold')

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='#00d4aa', label='High scoring'),
        mpatches.Patch(facecolor='#ffa502', label='Moderate'),
        mpatches.Patch(facecolor='#ff6b6b', label='Low scoring'),
        mpatches.Patch(facecolor='#ff0000', label='Drought zone'),
    ]
    ax3.legend(handles=legend_elements, loc='upper right', fontsize=9,
               facecolor='#16213e', edgecolor=text_color, labelcolor=text_color)

    # 4. Top 10 longest droughts (bottom left)
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.set_facecolor('#16213e')
    top_droughts = sorted(sig_droughts, key=lambda x: x['duration'], reverse=True)[:10]
    y_pos = np.arange(len(top_droughts))
    durations_min = [d['duration'] / 60 for d in top_droughts]
    labels = [f"{d['game'][:30]}" for d in top_droughts]

    bars4 = ax4.barh(y_pos, durations_min, color='#ff6b6b', edgecolor='#ffffff', linewidth=0.3, height=0.7)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(labels, fontsize=8, color=text_color)
    ax4.set_xlabel('Duration (minutes)', fontsize=10, color=text_color)
    ax4.set_title('Top 10 Longest Droughts', fontsize=13, fontweight='bold', color=title_color, pad=10)
    ax4.tick_params(colors=text_color)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    ax4.spines['bottom'].set_color(text_color)
    ax4.spines['left'].set_color(text_color)
    ax4.invert_yaxis()
    for bar, d in zip(bars4, top_droughts):
        ax4.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                 f"{format_time(d['duration'])} (min {d['start']//60}-{d['end']//60})",
                 va='center', color=text_color, fontsize=8)

    # 5. Opening score time distribution (bottom right)
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.set_facecolor('#16213e')
    opening_times = [d['duration'] / 60 for d in all_droughts if d['start'] == 0]
    
    bins = [0, 1, 2, 3, 4, 5, 7, 10, 15]
    counts, edges = np.histogram(opening_times, bins=bins)
    bin_labels = [f'{int(edges[i])}-{int(edges[i+1])}' for i in range(len(edges)-1)]
    colors5 = ['#00d4aa' if edges[i+1] <= 3 else '#ffa502' if edges[i+1] <= 5 else '#ff6b6b' for i in range(len(edges)-1)]
    
    ax5.bar(bin_labels, counts, color=colors5, edgecolor='#ffffff', linewidth=0.5, width=0.7)
    ax5.set_title('Time to First Score (minutes)', fontsize=13, fontweight='bold', color=title_color, pad=10)
    ax5.set_xlabel('Minutes', fontsize=10, color=text_color)
    ax5.set_ylabel('Number of Games', fontsize=10, color=text_color)
    ax5.tick_params(colors=text_color)
    ax5.spines['top'].set_visible(False)
    ax5.spines['right'].set_visible(False)
    ax5.spines['bottom'].set_color(text_color)
    ax5.spines['left'].set_color(text_color)
    avg_open = sum(opening_times) / len(opening_times) if opening_times else 0
    ax5.axvline(x=len(bins)//2 - 0.5, color=warning_color, linestyle=':', alpha=0)  # hidden
    ax5.text(0.95, 0.90, f'Avg: {avg_open:.1f} min\n39% take 5+ min',
             transform=ax5.transAxes, ha='right', va='top', color=highlight_color, fontsize=10,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#0f3460', edgecolor=highlight_color, alpha=0.8))

    # 6. Key insights panel (bottom row)
    ax6 = fig.add_subplot(gs[3, :])
    ax6.set_facecolor('#0f3460')
    ax6.set_xlim(0, 10)
    ax6.set_ylim(0, 10)
    ax6.axis('off')

    ax6.text(5, 9.2, 'KEY PATTERNS & TACTICAL INSIGHTS', ha='center', fontsize=14,
             fontweight='bold', color=highlight_color)

    insights = [
        ('[!] DANGER ZONE 1:', 'Opening 10 minutes -- 28 droughts start here (2x any other phase). Team is slow to get going.'),
        ('[!] DANGER ZONE 2:', 'Start of 2nd half (30-40 min) -- 18 droughts start here. Post-halftime lull is real.'),
        ('[*] CROSS-HALF:', '13 droughts span halftime -- momentum frequently lost around the break.'),
        ('[+] STRONG FINISH:', 'Last 10 min has fewest droughts & shortest avg duration (3:19). Urgency helps.'),
        ('[=] OVERALL:', f'Avg significant drought: 8:57. 1st half droughts avg 22 sec longer than 2nd half.'),
    ]

    for i, (label, text) in enumerate(insights):
        y = 7.5 - i * 1.5
        ax6.text(0.3, y, label, fontsize=11, fontweight='bold', color=warning_color if '🔴' in label or '🟠' in label else accent_color, va='center')
        ax6.text(2.8, y, text, fontsize=10, color=text_color, va='center', wrap=True)

    output_path = os.path.join(data_dir, 'killinkere_drought_infographic.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Infographic saved to: {output_path}")

if __name__ == '__main__':
    main()
