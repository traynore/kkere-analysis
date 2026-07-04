#!/usr/bin/env python3
"""Analyze scoring drought patterns for Killinkere across all games."""

import csv
import os
import glob
from datetime import timedelta
import re

def parse_time(time_str):
    """Parse time string (HH:MM:SS or MM:SS) to total seconds."""
    parts = time_str.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

def format_time(seconds):
    """Format seconds back to MM:SS."""
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def is_killinkere_score(row, headers):
    """Check if this row is a Killinkere score event."""
    team_col = 'Team Name' if 'Team Name' in headers else headers.get('team', 'Team Name')
    
    team = row.get('Team Name', '')
    name = row.get('Name', '')
    outcome = row.get('Outcome', '')
    
    score_events = ['Shot from play', 'Scoreable free']
    score_outcomes = ['Point', '2 Points', 'Goal']
    
    return (team == 'Killinkere' and 
            name in score_events and 
            outcome in score_outcomes)

def get_period(row):
    """Get game period from row."""
    return row.get('Period', row.get('Game Period', '1'))

def analyze_game(filepath):
    """Analyze a single game for scoring droughts."""
    droughts = []
    
    try:
        # Try different encodings
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        # Handle potential extra content after main CSV (like team lists)
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        csv_lines = []
        for line in lines:
            if line.startswith('=') or line == '':
                break
            csv_lines.append(line)
        
        if not csv_lines:
            return []
        
        reader = csv.DictReader(csv_lines)
        
        scores = []
        game_start = 0
        game_end = 0
        
        for row in reader:
            time_str = row.get('Time', '')
            if not time_str:
                continue
            
            time_sec = parse_time(time_str)
            game_end = max(game_end, time_sec)
            
            if is_killinkere_score(row, reader.fieldnames):
                period = get_period(row)
                scores.append({
                    'time': time_sec,
                    'period': period,
                    'time_str': time_str
                })
        
        if not scores:
            # Entire game was a drought
            if game_end > 0:
                droughts.append({
                    'start': 0,
                    'end': game_end,
                    'duration': game_end,
                    'start_period': '1',
                    'end_period': '2'
                })
            return droughts
        
        # Drought from game start to first score
        if scores[0]['time'] > 0:
            droughts.append({
                'start': 0,
                'end': scores[0]['time'],
                'duration': scores[0]['time'],
                'start_period': '1',
                'end_period': scores[0]['period']
            })
        
        # Droughts between consecutive scores
        for i in range(len(scores) - 1):
            gap = scores[i+1]['time'] - scores[i]['time']
            droughts.append({
                'start': scores[i]['time'],
                'end': scores[i+1]['time'],
                'duration': gap,
                'start_period': scores[i]['period'],
                'end_period': scores[i+1]['period']
            })
        
        # Drought from last score to game end
        if scores[-1]['time'] < game_end:
            droughts.append({
                'start': scores[-1]['time'],
                'end': game_end,
                'duration': game_end - scores[-1]['time'],
                'start_period': scores[-1]['period'],
                'end_period': '2'
            })
        
    except Exception as e:
        print(f"  Error processing {os.path.basename(filepath)}: {e}")
        return []
    
    return droughts

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = glob.glob(os.path.join(data_dir, 'Killinkere*.csv'))
    
    all_droughts = []
    game_names = []
    
    print(f"Analyzing {len(csv_files)} games...\n")
    
    for filepath in sorted(csv_files):
        game_name = os.path.basename(filepath).replace('.csv', '')
        droughts = analyze_game(filepath)
        for d in droughts:
            d['game'] = game_name
        all_droughts.extend(droughts)
        game_names.append(game_name)
    
    # Filter to significant droughts (5+ minutes)
    sig_droughts = [d for d in all_droughts if d['duration'] >= 300]
    
    print("=" * 70)
    print("SCORING DROUGHT ANALYSIS - KILLINKERE")
    print("=" * 70)
    
    # 1. Top 15 longest droughts
    print("\n--- TOP 15 LONGEST SCORING DROUGHTS ---")
    sig_droughts.sort(key=lambda x: x['duration'], reverse=True)
    for i, d in enumerate(sig_droughts[:15], 1):
        print(f"  {i:2d}. {format_time(d['duration'])} "
              f"({format_time(d['start'])} -> {format_time(d['end'])}) "
              f"Period {d['start_period']}->{d['end_period']} "
              f"| {d['game'][:50]}")
    
    # 2. Analyze when droughts occur by game time
    print("\n\n--- DROUGHT DISTRIBUTION BY GAME PHASE ---")
    # Split game into phases (assuming ~60 min game: 0-10, 10-20, 20-30 = 1st half; 30-40, 40-50, 50-60 = 2nd half)
    phases = {
        '1H Start (0-10 min)': (0, 600),
        '1H Middle (10-20 min)': (600, 1200),
        '1H End (20-30 min)': (1200, 1800),
        '2H Start (30-40 min)': (1800, 2400),
        '2H Middle (40-50 min)': (2400, 3000),
        '2H End (50-60 min)': (3000, 3600),
    }
    
    # Count droughts that START in each phase
    print("\n  Droughts (5+ min) STARTING in each phase:")
    for phase_name, (start, end) in phases.items():
        count = sum(1 for d in sig_droughts if start <= d['start'] < end)
        bar = '█' * count
        print(f"    {phase_name:25s}: {count:3d} {bar}")
    
    # Count droughts that OVERLAP each phase
    print("\n  Droughts (5+ min) ACTIVE during each phase:")
    for phase_name, (start, end) in phases.items():
        count = sum(1 for d in sig_droughts if d['start'] < end and d['end'] > start)
        bar = '█' * count
        print(f"    {phase_name:25s}: {count:3d} {bar}")
    
    # 3. Average drought duration by phase
    print("\n  Average drought duration (all droughts) by START phase:")
    for phase_name, (start, end) in phases.items():
        phase_droughts = [d for d in all_droughts if start <= d['start'] < end and d['duration'] > 0]
        if phase_droughts:
            avg = sum(d['duration'] for d in phase_droughts) / len(phase_droughts)
            print(f"    {phase_name:25s}: {format_time(int(avg))} avg ({len(phase_droughts)} droughts)")
        else:
            print(f"    {phase_name:25s}: N/A")
    
    # 4. Period analysis (1st half vs 2nd half)
    print("\n\n--- 1ST HALF vs 2ND HALF DROUGHTS ---")
    h1_droughts = [d for d in sig_droughts if d['start'] < 1800]
    h2_droughts = [d for d in sig_droughts if d['start'] >= 1800]
    
    h1_avg = sum(d['duration'] for d in h1_droughts) / max(len(h1_droughts), 1)
    h2_avg = sum(d['duration'] for d in h2_droughts) / max(len(h2_droughts), 1)
    
    print(f"  1st Half: {len(h1_droughts)} droughts, avg duration {format_time(int(h1_avg))}")
    print(f"  2nd Half: {len(h2_droughts)} droughts, avg duration {format_time(int(h2_avg))}")
    
    # 5. Cross-half droughts (spanning halftime)
    cross_half = [d for d in sig_droughts if d['start'] < 1800 and d['end'] > 1800]
    print(f"\n  Droughts spanning halftime: {len(cross_half)}")
    for d in sorted(cross_half, key=lambda x: x['duration'], reverse=True)[:5]:
        print(f"    {format_time(d['duration'])} ({format_time(d['start'])} -> {format_time(d['end'])}) | {d['game'][:45]}")
    
    # 6. End-of-half scoring issues
    print("\n\n--- END-OF-HALF PATTERNS ---")
    late_1h = [d for d in sig_droughts if d['start'] >= 1200 and d['start'] < 1800]
    late_2h = [d for d in sig_droughts if d['start'] >= 3000]
    print(f"  Droughts starting in last 10 min of 1st half (20-30 min): {len(late_1h)}")
    print(f"  Droughts starting in last 10 min of 2nd half (50-60 min): {len(late_2h)}")
    
    # 7. Opening drought patterns
    print("\n\n--- OPENING SCORING PATTERNS ---")
    opening_droughts = [d for d in all_droughts if d['start'] == 0]
    if opening_droughts:
        avg_first_score = sum(d['duration'] for d in opening_droughts) / len(opening_droughts)
        max_first = max(d['duration'] for d in opening_droughts)
        min_first = min(d['duration'] for d in opening_droughts)
        print(f"  Time to first score (avg): {format_time(int(avg_first_score))}")
        print(f"  Time to first score (max): {format_time(max_first)}")
        print(f"  Time to first score (min): {format_time(min_first)}")
        print(f"  Games taking 5+ min to score: {sum(1 for d in opening_droughts if d['duration'] >= 300)}/{len(opening_droughts)}")
    
    # 8. Summary stats
    print("\n\n--- SUMMARY ---")
    print(f"  Total games analyzed: {len(csv_files)}")
    print(f"  Total scoring droughts (5+ min): {len(sig_droughts)}")
    if sig_droughts:
        print(f"  Average significant drought: {format_time(int(sum(d['duration'] for d in sig_droughts) / len(sig_droughts)))}")
        print(f"  Longest drought: {format_time(sig_droughts[0]['duration'])}")
    
    # 9. Per-game drought count
    print("\n\n--- GAMES WITH MOST SIGNIFICANT DROUGHTS (5+ min) ---")
    game_drought_count = {}
    for d in sig_droughts:
        game_drought_count[d['game']] = game_drought_count.get(d['game'], 0) + 1
    
    for game, count in sorted(game_drought_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count} droughts: {game[:60]}")

if __name__ == '__main__':
    main()
