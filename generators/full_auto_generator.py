#!/usr/bin/env python3
"""
FULL AUTOMATION - Complete Infographic Generator
Calculates ALL statistics from CSV and generates complete HTML
Usage: python3 full_auto_generator.py <csv_file>
"""

import csv
import sys
import re
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

def read_metadata(csv_filename):
    """Read metadata from .meta file if it exists"""
    meta_file = Path(csv_filename).with_suffix('.meta')
    metadata = {'venue': '', 'date': '', 'time': '', 'competition': ''}
    
    if not meta_file.exists():
        # Try fuzzy match for filenames with spacing differences
        stem = Path(csv_filename).stem
        for candidate in Path(csv_filename).parent.glob('*.meta'):
            if candidate.stem.replace(' ', '') == stem.replace(' ', ''):
                meta_file = candidate
                break
    
    if meta_file.exists():
        with open(meta_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    metadata[key] = value
    
    return metadata

def calc_all_stats(events, csv_filename):
    """Calculate ALL statistics needed for the infographic"""
    # Killinkere is always team1 (green)
    all_teams = set(e['Team Name'] for e in events if e.get('Team Name'))
    
    if 'Killinkere' in all_teams:
        t1 = 'Killinkere'
        t2 = [t for t in all_teams if t != 'Killinkere'][0]
    else:
        # Fallback: parse filename
        filename = Path(csv_filename).stem
        import re
        match = re.match(r'(.+?)\s+\d+\s*-\s*\d+\s+v\s+\d+\s*-\s*\d+\s+(.+)', filename)
        if match:
            t1, t2 = match.group(1).strip(), match.group(2).strip()
        else:
            teams = sorted(all_teams)
            t1, t2 = teams[0], teams[1]
    
    stats = {'team1': t1, 'team2': t2}
    
    # Calculate scores
    for team, prefix in [(t1, 't1'), (t2, 't2')]:
        team_events = [e for e in events if e['Team Name'] == team]
        
        # ALL scoring events for total score
        all_scoring = [e for e in team_events if e.get('Name') in ['Shot from play', 'Scoreable free']]
        total_goals = len([s for s in all_scoring if s['Outcome'] == 'Goal'])
        total_points = len([s for s in all_scoring if s['Outcome'] == 'Point'])
        total_two_pts = len([s for s in all_scoring if s['Outcome'] == '2 Points'])
        
        # ONLY Shot from play for accuracy calculation
        shots_from_play = [e for e in team_events if e.get('Name') == 'Shot from play']
        play_goals = len([s for s in shots_from_play if s['Outcome'] == 'Goal'])
        play_points = len([s for s in shots_from_play if s['Outcome'] == 'Point'])
        play_two_pts = len([s for s in shots_from_play if s['Outcome'] == '2 Points'])
        wides = len([s for s in shots_from_play if s['Outcome'] == 'Wide'])
        shorts = len([s for s in shots_from_play if s['Outcome'] == 'Short'])
        fortyfives = len([s for s in shots_from_play if s['Outcome'] == '45'])
        
        stats[f'{prefix}_goals'] = total_goals
        stats[f'{prefix}_points'] = total_points
        stats[f'{prefix}_points_from_play'] = play_points
        stats[f'{prefix}_two_pts'] = total_two_pts
        stats[f'{prefix}_total_score'] = total_goals * 3 + total_points + total_two_pts * 2
        stats[f'{prefix}_shots_total'] = len(shots_from_play)
        stats[f'{prefix}_shots_scored'] = play_goals + play_points + play_two_pts
        stats[f'{prefix}_wides'] = wides
        stats[f'{prefix}_shorts'] = shorts
        stats[f'{prefix}_45s'] = fortyfives
        # Accuracy = scored / total shots
        stats[f'{prefix}_acc'] = round((stats[f'{prefix}_shots_scored'] / len(shots_from_play) * 100), 1) if len(shots_from_play) > 0 else 0
        
        # Period stats
        for period, psuffix in [(1, 'p1'), (2, 'p2')]:
            period_events = [e for e in team_events if e.get('Period') == str(period)]
            
            # ALL scoring for period score (Shot from play + Scoreable free)
            period_all_scoring = [e for e in period_events if e.get('Name') in ['Shot from play', 'Scoreable free']]
            p_goals_all = len([s for s in period_all_scoring if s['Outcome'] == 'Goal'])
            p_points_all = len([s for s in period_all_scoring if s['Outcome'] == 'Point'])
            p_two_pts_all = len([s for s in period_all_scoring if s['Outcome'] == '2 Points'])
            
            # ONLY Shot from play for accuracy
            period_shots = [e for e in period_events if e.get('Name') == 'Shot from play']
            p_goals = len([s for s in period_shots if s['Outcome'] == 'Goal'])
            p_points = len([s for s in period_shots if s['Outcome'] == 'Point'])
            p_two_pts = len([s for s in period_shots if s['Outcome'] == '2 Points'])
            
            stats[f'{prefix}_{psuffix}_goals'] = p_goals_all
            stats[f'{prefix}_{psuffix}_points'] = p_points_all
            stats[f'{prefix}_{psuffix}_two_pts'] = p_two_pts_all
            stats[f'{prefix}_{psuffix}_total'] = p_goals_all * 3 + p_points_all + p_two_pts_all * 2
            stats[f'{prefix}_{psuffix}_shots_total'] = len(period_shots)
            stats[f'{prefix}_{psuffix}_shots_scored'] = p_goals + p_points + p_two_pts
            # Accuracy = scored / total shots
            stats[f'{prefix}_{psuffix}_acc'] = round((stats[f'{prefix}_{psuffix}_shots_scored'] / len(period_shots) * 100), 1) if len(period_shots) > 0 else 0
        
        # Kickouts
        kickouts = [e for e in team_events if e.get('Name') == 'Kickout']
        stats[f'{prefix}_ko_wc'] = len([k for k in kickouts if k['Outcome'] == 'Won clean'])
        stats[f'{prefix}_ko_sw'] = len([k for k in kickouts if k['Outcome'] == 'Short won'])
        stats[f'{prefix}_ko_bw'] = len([k for k in kickouts if k['Outcome'] == 'Break won'])
        stats[f'{prefix}_ko_lc'] = len([k for k in kickouts if k['Outcome'] == 'Lost clean'])
        stats[f'{prefix}_ko_bl'] = len([k for k in kickouts if k['Outcome'] == 'Break lost'])
        stats[f'{prefix}_ko_sl'] = len([k for k in kickouts if k['Outcome'] == 'Sideline ball'])
        stats[f'{prefix}_ko_won'] = stats[f'{prefix}_ko_wc'] + stats[f'{prefix}_ko_sw'] + stats[f'{prefix}_ko_bw']
        stats[f'{prefix}_ko_total'] = stats[f'{prefix}_ko_won'] + stats[f'{prefix}_ko_lc'] + stats[f'{prefix}_ko_bl'] + stats[f'{prefix}_ko_sl']
        stats[f'{prefix}_ko_pct'] = round((stats[f'{prefix}_ko_won'] / stats[f'{prefix}_ko_total'] * 100)) if stats[f'{prefix}_ko_total'] > 0 else 0
        
        # Other stats
        stats[f'{prefix}_turnovers'] = len([e for e in team_events if e.get('Name') in ['Turnover', 'Ball Won']])
        poss_lost = [e for e in team_events if e.get('Name') == 'Possession lost']
        stats[f'{prefix}_poss_lost'] = len(poss_lost)
        stats[f'{prefix}_poss_lost_contact'] = len([e for e in poss_lost if e.get('Outcome') == 'In Contact'])
        stats[f'{prefix}_poss_lost_handpass'] = len([e for e in poss_lost if e.get('Outcome') == 'Hand pass'])
        stats[f'{prefix}_poss_lost_kickpass'] = len([e for e in poss_lost if e.get('Outcome') == 'Kick pass'])
        stats[f'{prefix}_poss_lost_handling'] = len([e for e in poss_lost if e.get('Outcome') == 'Handling'])
        stats[f'{prefix}_frees_conc'] = len([e for e in team_events if e.get('Name') == 'Free conceded'])
        stats[f'{prefix}_frees_defensive'] = len([e for e in team_events if e.get('Name') == 'Free conceded' and e.get('Outcome') == 'Defensive third'])
        stats[f'{prefix}_frees_middle'] = len([e for e in team_events if e.get('Name') == 'Free conceded' and e.get('Outcome') == 'Middle third'])
        stats[f'{prefix}_frees_attacking'] = len([e for e in team_events if e.get('Name') == 'Free conceded' and e.get('Outcome') == 'Attacking third'])
        
        # Calculate scores conceded from frees
        points_from_frees = 0
        for i, e in enumerate(events):
            if e['Team Name'] == team and e.get('Name') == 'Free conceded':
                # Look ahead up to 5 events for opposition scoreable free that scored
                for j in range(i + 1, min(i + 6, len(events))):
                    next_event = events[j]
                    # Stop if we hit another scoring event or free conceded
                    if next_event.get('Name') in ['Shot from play', 'Free conceded']:
                        break
                    if next_event['Team Name'] != team and next_event.get('Name') == 'Scoreable free':
                        outcome = next_event.get('Outcome')
                        if outcome == 'Goal':
                            points_from_frees += 3
                        elif outcome == '2 Points':
                            points_from_frees += 2
                        elif outcome == 'Point':
                            points_from_frees += 1
                        break
        stats[f'{prefix}_points_from_frees'] = points_from_frees
        stats[f'{prefix}_attacks'] = len([e for e in team_events if e.get('Name') == 'Attacks'])
        stats[f'{prefix}_attacks_shot'] = len([e for e in team_events if e.get('Name') == 'Attacks' and e.get('Outcome') == 'Shot taken'])
        
        # Scoreable frees
        sf = [e for e in team_events if e.get('Name') == 'Scoreable free']
        stats[f'{prefix}_sf_total'] = len(sf)
        stats[f'{prefix}_sf_goals'] = len([s for s in sf if s['Outcome'] == 'Goal'])
        stats[f'{prefix}_sf_points'] = len([s for s in sf if s['Outcome'] == 'Point'])
        stats[f'{prefix}_sf_two_pts'] = len([s for s in sf if s['Outcome'] == '2 Points'])
        stats[f'{prefix}_sf_wides'] = len([s for s in sf if s['Outcome'] == 'Wide'])
        stats[f'{prefix}_sf_shorts'] = len([s for s in sf if s['Outcome'] == 'Short'])
        stats[f'{prefix}_sf_scored'] = stats[f'{prefix}_sf_goals'] + stats[f'{prefix}_sf_points'] + stats[f'{prefix}_sf_two_pts']
        stats[f'{prefix}_sf_acc'] = round((stats[f'{prefix}_sf_scored'] / stats[f'{prefix}_sf_total'] * 100)) if stats[f'{prefix}_sf_total'] > 0 else 0
        
        # Identify which scoreable frees came from 45s
        sf_from_45_indices = set()
        for i, e in enumerate(events):
            if e['Team Name'] == team and e.get('Name') == 'Shot from play' and e.get('Outcome') == '45':
                for j in range(i + 1, min(i + 5, len(events))):
                    n = events[j]
                    if n['Team Name'] == team and n.get('Name') == 'Scoreable free':
                        sf_from_45_indices.add(int(n.get('Event', j)))
                        break
                    if n.get('Name') in ['Shot from play', 'Free conceded', 'Kickout']:
                        break
        sf_from_45 = [s for s in sf if int(s.get('Event', 0)) in sf_from_45_indices]
        stats[f'{prefix}_sf45_total'] = len(sf_from_45)
        stats[f'{prefix}_sf45_scored'] = len([s for s in sf_from_45 if s['Outcome'] in ['Goal', 'Point', '2 Points']])
        
        # Points value scored from frees (fouls) vs from 45s for score breakdown
        sf_from_fouls = [s for s in sf if int(s.get('Event', 0)) not in sf_from_45_indices]
        sf_foul_pts = sum(3 if s['Outcome']=='Goal' else 2 if s['Outcome']=='2 Points' else 1 for s in sf_from_fouls if s['Outcome'] in ['Goal','Point','2 Points'])
        sf_45_pts = sum(3 if s['Outcome']=='Goal' else 2 if s['Outcome']=='2 Points' else 1 for s in sf_from_45 if s['Outcome'] in ['Goal','Point','2 Points'])
        stats[f'{prefix}_pts_from_fouls'] = sf_foul_pts
        stats[f'{prefix}_pts_from_45s'] = sf_45_pts
    
    # Player stats
    for team, prefix in [(t1, 't1'), (t2, 't2')]:
        team_events = [e for e in events if e['Team Name'] == team]
        players = defaultdict(lambda: {'goals': 0, 'points': 0, 'two_pts': 0, 'shots': 0, 'scored': 0, 'free_attempts': 0, 'frees_scored': 0, 'free_goals': 0, 'free_points': 0, 'free_two_pts': 0, 'turnovers': 0, 'poss_lost': 0, 'frees': 0, 'kickouts': 0})
        
        for e in team_events:
            if not e.get('Player'):
                continue
            player = e['Player']
            
            if e.get('Name') == 'Shot from play':
                players[player]['shots'] += 1
                if e['Outcome'] == 'Goal':
                    players[player]['goals'] += 1
                    players[player]['scored'] += 1
                elif e['Outcome'] == 'Point':
                    players[player]['points'] += 1
                    players[player]['scored'] += 1
                elif e['Outcome'] == '2 Points':
                    players[player]['two_pts'] += 1
                    players[player]['scored'] += 1
            
            if e.get('Name') == 'Scoreable free':
                players[player]['free_attempts'] += 1
                if e['Outcome'] == 'Goal':
                    players[player]['goals'] += 1
                    players[player]['frees_scored'] += 1
                    players[player]['free_goals'] += 1
                elif e['Outcome'] == 'Point':
                    players[player]['points'] += 1
                    players[player]['frees_scored'] += 1
                    players[player]['free_points'] += 1
                elif e['Outcome'] == '2 Points':
                    players[player]['two_pts'] += 1
                    players[player]['frees_scored'] += 1
                    players[player]['free_two_pts'] += 1
            
            if e.get('Name') in ['Turnover', 'Ball Won']:
                players[player]['turnovers'] += 1
            if e.get('Name') == 'Possession lost':
                players[player]['poss_lost'] += 1
            if e.get('Name') == 'Free conceded':
                players[player]['frees'] += 1
            if e.get('Name') == 'Kickout' and e.get('Outcome') in ['Won clean', 'Short won', 'Break won']:
                players[player]['kickouts'] += 1
        
        # Sort by total score
        sorted_players = sorted(players.items(), key=lambda x: (x[1]['goals'] * 3 + x[1]['points'] + x[1]['two_pts'] * 2, x[1]['shots']), reverse=True)
        stats[f'{prefix}_players'] = [(name, data) for name, data in sorted_players if data['goals'] > 0 or data['points'] > 0 or data['two_pts'] > 0 or data['shots'] > 0][:10]
    
    # Generate timeline data — scores + bookings
    scoring_events = [e for e in events if e.get('Name') in ['Shot from play', 'Scoreable free'] and e.get('Outcome') in ['Goal', 'Point', '2 Points']]
    booking_events = [e for e in events if e.get('Name') == 'Bookings']
    timeline_events = scoring_events + booking_events
    timeline_events.sort(key=lambda x: (int(x.get('Period', '1')), x.get('Time', '00:00:00')))
    
    timeline = []
    t1_score = 0
    t2_score = 0
    
    for e in timeline_events:
        is_booking = e.get('Name') == 'Bookings'
        if not is_booking:
            pts = 3 if e['Outcome'] == 'Goal' else (2 if e['Outcome'] == '2 Points' else 1)
            if e['Team Name'] == t1:
                t1_score += pts
            else:
                t2_score += pts
        
        timeline.append({
            'time': e.get('Time', ''),
            'period': e.get('Period', '1'),
            'team': e['Team Name'],
            'outcome': e['Outcome'],
            'player': e.get('Player', ''),
            'name': e.get('Name', ''),
            't1_score': t1_score,
            't2_score': t2_score,
            'is_booking': is_booking
        })
    
    stats['timeline'] = timeline
    
    # Check if team1 scored first after halftime
    p2_scores = [e for e in timeline if e['period'] == '2' and not e.get('is_booking')]
    stats['scored_first_after_ht'] = len(p2_scores) > 0 and p2_scores[0]['team'] == t1
    if stats['scored_first_after_ht']:
        stats['first_score_after_ht_idx'] = len([e for e in timeline if e['period'] == '1']) + 1  # +1 for 'Start'
    else:
        stats['first_score_after_ht_idx'] = -1
    
    return stats

def generate_html(csv_file):
    """Generate complete HTML with all data"""
    
    print(f"\n{'='*60}")
    print("FULL AUTOMATION - Generating Complete Infographic")
    print(f"{'='*60}\n")
    
    # Calculate 2026 season stats from all Killinkere CSV files (auto-discovered, sorted by date)
    from datetime import datetime
    data_dir = Path(csv_file).parent if Path(csv_file).is_absolute() else Path(csv_file).resolve().parent
    all_csv_files = [str(p.name) for p in data_dir.glob('Killinkere*.csv')]
    def get_game_date(csv_name):
        meta = read_metadata(str(data_dir / csv_name))
        if meta['date']:
            try:
                return datetime.strptime(meta['date'], '%d/%m/%Y')
            except ValueError:
                pass
        return datetime.max
    all_csvs = sorted(all_csv_files, key=get_game_date)
    total_shots_2026 = 0
    successful_shots_2026 = 0
    total_attacks_2026 = 0
    attacks_with_shot_2026 = 0
    goals_2026 = 0
    two_pointers_2026 = 0
    points_2026 = 0
    
    # Per-game accumulative tracking
    game_labels = []
    game_competitions = []  # competition category per game
    acc_accuracy = []       # accumulative accuracy per game
    acc_goals = []          # accumulative goals
    acc_two_pts = []        # accumulative 2 pointers
    acc_points = []         # accumulative points
    acc_attack_pct = []     # accumulative attack efficiency
    per_game_accuracy = []  # individual game accuracy
    per_game_attack_pct = [] # individual game attack efficiency
    
    for csv_path in all_csvs:
        full_path = str(data_dir / csv_path)
        if Path(full_path).exists():
            csv_events = read_csv(full_path)
            game_shots = 0
            game_scored = 0
            for e in csv_events:
                if e['Team Name'] == 'Killinkere':
                    if e.get('Name') == 'Shot from play':
                        total_shots_2026 += 1
                        game_shots += 1
                        outcome = e.get('Outcome')
                        if outcome in ['Point', 'Goal', '2 Points']:
                            successful_shots_2026 += 1
                            game_scored += 1
                    if e.get('Name') in ['Shot from play', 'Scoreable free']:
                        outcome = e.get('Outcome')
                        if outcome == 'Goal':
                            goals_2026 += 1
                        elif outcome == '2 Points':
                            two_pointers_2026 += 1
                        elif outcome == 'Point':
                            points_2026 += 1
                    if e.get('Name') == 'Attacks':
                        if e.get('Outcome') == 'Shot taken':
                            attacks_with_shot_2026 += 1
            # Only count total attacks for games where attacks were properly tagged
            game_events = [e for e in csv_events if e['Team Name'] == 'Killinkere']
            game_attacks = [e for e in game_events if e.get('Name') == 'Attacks']
            game_attack_shots = [e for e in game_attacks if e.get('Outcome') == 'Shot taken']
            if len(game_attack_shots) > 0:
                total_attacks_2026 += len(game_attacks)
            
            # Extract opponent name for label
            opponent = re.search(r'v\s+\d+\s*-\s*\d+\s+(.+)\.csv', csv_path)
            label = opponent.group(1).strip() if opponent else csv_path.replace('.csv', '')
            game_labels.append(label)
            
            # Competition category
            game_meta = read_metadata(full_path)
            comp = game_meta.get('competition', '').lower().strip()
            if 'spring' in comp or 'ulster' in comp:
                game_competitions.append('Spring League')
            elif 'challenge' in comp:
                game_competitions.append('Challenge')
            elif 'div 3' in comp or 'div3' in comp:
                game_competitions.append('ACFL Div 3')
            elif 'div' in comp:
                game_competitions.append('ACFL Div 7')
            else:
                game_competitions.append('Other')
            
            # Accumulative stats after this game
            acc_accuracy.append(round((successful_shots_2026 / total_shots_2026 * 100), 1) if total_shots_2026 > 0 else 0)
            acc_goals.append(goals_2026)
            acc_two_pts.append(two_pointers_2026)
            acc_points.append(points_2026)
            acc_attack_pct.append(round((attacks_with_shot_2026 / total_attacks_2026 * 100), 1) if total_attacks_2026 > 0 else 0)
            per_game_accuracy.append(round((game_scored / game_shots * 100), 1) if game_shots > 0 else 0)
            per_game_attack_pct.append(round((len(game_attack_shots) / len(game_attacks) * 100), 1) if len(game_attacks) > 0 else 0)
    
    year_2026_accuracy = round((successful_shots_2026 / total_shots_2026 * 100), 1) if total_shots_2026 > 0 else 0
    attacks_2026_pct = round((attacks_with_shot_2026 / total_attacks_2026 * 100), 1) if total_attacks_2026 > 0 else 0
    
    # Read CSV
    print(f"📊 Reading: {csv_file}")
    events = read_csv(csv_file)
    
    # Read metadata
    metadata = read_metadata(csv_file)
    
    # Calculate stats
    print(f"🔢 Calculating statistics...")
    stats = calc_all_stats(events, csv_file)
    
    print(f"✓ Teams: {stats['team1']} vs {stats['team2']}")
    print(f"✓ Score: {stats['t1_goals']}-{stats['t1_points']+stats['t1_two_pts']*2} ({stats['t1_total_score']}) vs {stats['t2_goals']}-{stats['t2_points']+stats['t2_two_pts']*2} ({stats['t2_total_score']})")
    print(f"✓ Found {len(stats['t1_players'])} players for {stats['team1']}")
    print(f"✓ Found {len(stats['t2_players'])} players for {stats['team2']}")
    
    # Read template
    template_file = 'advanced_infographic.html'
    if not Path(template_file).exists():
        print(f"\n❌ Error: Template '{template_file}' not found")
        return None
    
    print(f"📝 Reading template...")
    with open(template_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(f"🔄 Replacing all data points...")
    
    # Replace overall accuracy in period tab BEFORE team name replacement
    html = html.replace('<strong>Killinkere:</strong> 58%', f'<strong>TEAM1_PLACEHOLDER:</strong> {stats["t1_acc"]}%')
    html = html.replace('<strong>Aughadrumsee:</strong> 50%', f'<strong>TEAM2_PLACEHOLDER:</strong> {stats["t2_acc"]}%')
    
    # Replace team names (header first, then rest)
    html = re.sub(r'(<div class="team-name killinkere">)KILLINKERE(</div>)',
                  f'\\1{stats["team1"].upper()}\\2', html, count=1)
    html = re.sub(r'(<div class="team-name aughadrumsee">)KILLINKERE(</div>)',
                  f'\\1{stats["team2"].upper()}\\2', html, count=1)
    
    html = html.replace('Killinkere', stats['team1'])
    html = html.replace('KILLINKERE', stats['team1'].upper())
    html = html.replace('Aughadrumsee', stats['team2'])
    html = html.replace('AUGHADRUMSEE', stats['team2'].upper())
    
    # Replace team placeholders in accuracy section
    html = html.replace('TEAM1_PLACEHOLDER', stats['team1'])
    html = html.replace('TEAM2_PLACEHOLDER', stats['team2'])
    
    # Replace competition
    if metadata['competition']:
        html = html.replace('<div style="font-size: 1.3em; margin-bottom: 15px; opacity: 0.95;">TBD</div>',
                          f'<div style="font-size: 1.3em; margin-bottom: 15px; opacity: 0.95;">{metadata["competition"]}</div>')
    else:
        html = html.replace('<div style="font-size: 1.3em; margin-bottom: 15px; opacity: 0.95;">TBD</div>', '')
    
    # Replace scores in header
    html = re.sub(r'<div class="score-big killinkere">4-9</div>', 
                  f'<div class="score-big killinkere">{stats["t1_goals"]}-{stats["t1_points"]+stats["t1_two_pts"]*2}</div>', html)
    html = re.sub(r'<div class="score-breakdown">21 Points \(4 Goals, 9 Points\)</div>',
                  f'<div class="score-breakdown">{stats["t1_total_score"]} Points ({stats["t1_goals"]} Goals, {stats["t1_points"]+stats["t1_two_pts"]*2} Points)</div>', html, count=1)
    
    html = re.sub(r'<div class="score-big aughadrumsee">0-12</div>',
                  f'<div class="score-big aughadrumsee">{stats["t2_goals"]}-{stats["t2_points"]+stats["t2_two_pts"]*2}</div>', html)
    html = re.sub(r'<div class="score-breakdown">12 Points \(0 Goals, 12 Points\)</div>',
                  f'<div class="score-breakdown">{stats["t2_total_score"]} Points ({stats["t2_goals"]} Goals, {stats["t2_points"]+stats["t2_two_pts"]*2} Points)</div>', html)
    
    # Replace metadata
    html = html.replace('<strong>Venue:</strong> TBD', f'<strong>Venue:</strong> {metadata["venue"] or "TBD"}')
    html = html.replace('<strong>Date:</strong> TBD', f'<strong>Date:</strong> {metadata["date"] or "TBD"}')
    html = html.replace('<strong>Time:</strong> TBD', f'<strong>Time:</strong> {metadata["time"] or "TBD"}')
    
    # Replace shot accuracy
    html = re.sub(r'<div class="bar bar-killinkere" style="width: 58%">58%</div>',
                  f'<div class="bar bar-killinkere" style="width: {stats["t1_acc"]}%">{stats["t1_acc"]}%</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 50%">50%</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: {stats["t2_acc"]}%">{stats["t2_acc"]}%</div>', html, count=1)
    
    # Replace total shots/scores (use attacks_shot to match funnel)
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(19 \* 4%\)">19 / 11</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_attacks_shot"]} * 4%)">{stats["t1_attacks_shot"]} / {stats["t1_shots_scored"]}</div>', html)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(18 \* 4%\)">18 / 9</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_attacks_shot"]} * 4%)">{stats["t2_attacks_shot"]} / {stats["t2_shots_scored"]}</div>', html)
    
    # Replace score breakdown - Goals
    # Score Breakdown shows FROM PLAY only (frees shown separately)
    t1_goals_from_play = stats['t1_goals'] - stats['t1_sf_goals']
    t2_goals_from_play = stats['t2_goals'] - stats['t2_sf_goals']
    t1_two_pts_from_play = stats['t1_two_pts'] - stats['t1_sf_two_pts']
    t2_two_pts_from_play = stats['t2_two_pts'] - stats['t2_sf_two_pts']
    html = html.replace('T1_GOALS_VAL', str(t1_goals_from_play))
    html = html.replace('T2_GOALS_VAL', str(t2_goals_from_play))
    
    # Replace score breakdown - Points (from play only, frees shown separately)
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(7 \* 7%\)">7</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_points_from_play"]} * 7%)">{stats["t1_points_from_play"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(12 \* 7%\)">12</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_points_from_play"]} * 7%)">{stats["t2_points_from_play"]}</div>', html, count=1)
    
    # Replace 2 Points (from play only - context-aware to avoid collision with Handling)
    html = re.sub(r'(<div class="stat-label">2 Points \(from play\)</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({t1_two_pts_from_play} * 30%)">{t1_two_pts_from_play}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">2 Points \(from play\)</div>.*?bar-aughadrumsee" style=")width: [^"]+">[^<]+(</div>)',
                  f'\\1width: calc({t2_two_pts_from_play} * 30%)">{t2_two_pts_from_play}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace wides
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(7 \* 10%\)">7</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_wides"]} * 10%)">{stats["t1_wides"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(5 \* 10%\)">5</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_wides"]} * 10%)">{stats["t2_wides"]}</div>', html, count=1)
    
    # Replace kickout stats
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(20 \* 4%\)">20 / 17 \(85%\)</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_ko_total"]} * 4%)">{stats["t1_ko_total"]} / {stats["t1_ko_won"]} ({stats["t1_ko_pct"]}%)</div>', html)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(15 \* 4%\)">15 / 8 \(53%\)</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_ko_total"]} * 4%)">{stats["t2_ko_total"]} / {stats["t2_ko_won"]} ({stats["t2_ko_pct"]}%)</div>', html)
    
    # Replace kickout won clean (context-aware)
    html = re.sub(r'(<div class="stat-label">Kickouts Won Clean</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_ko_wc"]} * 10%)">{stats["t1_ko_wc"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Won Clean</div>.*?bar-aughadrumsee" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_ko_wc"]} * 10%)">{stats["t2_ko_wc"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace kickout short won (context-aware)
    html = re.sub(r'(<div class="stat-label">Kickouts Short Won</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_ko_sw"]} * 15%)">{stats["t1_ko_sw"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Short Won</div>.*?bar-aughadrumsee" style=")width: [^"]+">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_ko_sw"]} * 15%)">{stats["t2_ko_sw"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace kickout break won (context-aware)
    html = re.sub(r'(<div class="stat-label">Kickouts Break Won</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_ko_bw"]} * 20%)">{stats["t1_ko_bw"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Break Won</div>.*?bar-aughadrumsee" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_ko_bw"]} * 20%)">{stats["t2_ko_bw"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace kickout lost clean (context-aware)
    html = re.sub(r'(<div class="stat-label">Kickouts Lost Clean</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_ko_lc"]} * 25%)">{stats["t1_ko_lc"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Lost Clean</div>.*?bar-aughadrumsee" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_ko_lc"]} * 25%)">{stats["t2_ko_lc"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace kickout break lost (context-aware)
    html = re.sub(r'(<div class="stat-label">Kickouts Break Lost</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_ko_bl"]} * 20%)">{stats["t1_ko_bl"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Break Lost</div>.*?bar-aughadrumsee" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_ko_bl"]} * 20%)">{stats["t2_ko_bl"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace kickout sideline ball
    html = re.sub(r'(<div class="stat-label">Kickouts Sideline Ball</div>.*?bar-killinkere" style=")width: calc\(0 \* 25%\)">0(</div>)',
                  f'\\1width: calc({stats["t1_ko_sl"]} * 25%)">{stats["t1_ko_sl"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Kickouts Sideline Ball</div>.*?bar-aughadrumsee" style=")width: calc\(0 \* 25%\)">0(</div>)',
                  f'\\1width: calc({stats["t2_ko_sl"]} * 25%)">{stats["t2_ko_sl"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace possession lost total
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(13 \* 6%\)">13</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_poss_lost"]} * 6%)">{stats["t1_poss_lost"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 0%">0</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_poss_lost"]} * 6%)">{stats["t2_poss_lost"]}</div>', html, count=1)
    
    # Replace possession lost - in contact
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(6 \* 12%\)">6</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_poss_lost_contact"]} * 12%)">{stats["t1_poss_lost_contact"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 0%">0</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_poss_lost_contact"]} * 12%)">{stats["t2_poss_lost_contact"]}</div>', html, count=1)
    
    # Replace possession lost - hand pass
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(4 \* 15%\)">4</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_poss_lost_handpass"]} * 15%)">{stats["t1_poss_lost_handpass"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 0%">0</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_poss_lost_handpass"]} * 15%)">{stats["t2_poss_lost_handpass"]}</div>', html, count=1)
    
    # Replace possession lost - kick pass
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(3 \* 20%\)">3</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_poss_lost_kickpass"]} * 20%)">{stats["t1_poss_lost_kickpass"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 0%">0</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_poss_lost_kickpass"]} * 20%)">{stats["t2_poss_lost_kickpass"]}</div>', html, count=1)
    
    # Replace possession lost - handling (context-aware)
    html = re.sub(r'(<div class="stat-label">Poss\. Lost - Handling</div>.*?bar-killinkere" style=")width: calc\([^)]+\)">[^<]+(</div>)',
                  f'\\1width: calc({stats["t1_poss_lost_handling"]} * 30%)">{stats["t1_poss_lost_handling"]}\\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<div class="stat-label">Poss\. Lost - Handling</div>.*?bar-aughadrumsee" style=")width: [^"]+">[^<]+(</div>)',
                  f'\\1width: calc({stats["t2_poss_lost_handling"]} * 30%)">{stats["t2_poss_lost_handling"]}\\2', html, count=1, flags=re.DOTALL)
    
    # Replace turnovers
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(13 \* 6%\)">13</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_turnovers"]} * 6%)">{stats["t1_turnovers"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: 0%">0</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_turnovers"]} * 6%)">{stats["t2_turnovers"]}</div>', html, count=1)
    
    # Replace frees conceded
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(9 \* 9%\)">9</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_frees_conc"]} * 9%)">{stats["t1_frees_conc"]}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(2 \* 9%\)">2</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_frees_conc"]} * 9%)">{stats["t2_frees_conc"]}</div>', html, count=1)
    
    # Replace scores conceded from frees
    t1_pts_suffix = 'pt' if stats['t1_points_from_frees'] == 1 else 'pts'
    t2_pts_suffix = 'pt' if stats['t2_points_from_frees'] == 1 else 'pts'
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(3 \* 20%\)">3 pts</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_points_from_frees"]} * 20%)">{stats["t1_points_from_frees"]} {t1_pts_suffix}</div>', html, count=1)
    html = re.sub(r'<div class="bar bar-aughadrumsee" style="width: calc\(1 \* 20%\)">1 pt</div>',
                  f'<div class="bar bar-aughadrumsee" style="width: calc({stats["t2_points_from_frees"]} * 20%)">{stats["t2_points_from_frees"]} {t2_pts_suffix}</div>', html, count=1)
    
    # Replace funnel
    attacks_pct = round((stats['t1_attacks_shot'] / stats['t1_attacks'] * 100)) if stats['t1_attacks'] > 0 else 0
    funnel_missed = stats['t1_attacks_shot'] - stats['t1_shots_scored']
    funnel_no_shot = stats['t1_attacks'] - stats['t1_attacks_shot']
    funnel_score_pct = round(stats['t1_shots_scored'] / stats['t1_attacks'] * 100) if stats['t1_attacks'] > 0 else 0
    funnel_missed_pct = round(funnel_missed / stats['t1_attacks'] * 100) if stats['t1_attacks'] > 0 else 0
    funnel_no_shot_pct = 100 - funnel_score_pct - funnel_missed_pct
    html = html.replace('FUNNEL_ATTACKS', str(stats['t1_attacks']))
    html = html.replace('FUNNEL_SHOTS', str(stats['t1_attacks_shot']))
    html = html.replace('FUNNEL_SHOT_PCT', str(attacks_pct))
    html = html.replace('FUNNEL_SCORES', str(stats['t1_shots_scored']))
    html = html.replace('FUNNEL_ACC_PCT', str(stats['t1_acc']))
    html = html.replace('FUNNEL_SCORE_OF_ATTACK_PCT', str(funnel_score_pct))
    html = html.replace('FUNNEL_MISSED_OF_ATTACK_PCT', str(funnel_missed_pct))
    html = html.replace('FUNNEL_MISSED', str(funnel_missed))
    html = html.replace('FUNNEL_NO_SHOT_PCT', str(funnel_no_shot_pct))
    html = html.replace('FUNNEL_NO_SHOT', str(funnel_no_shot))

    # Shot map disabled for now — WIP
    html = html.replace('<!-- SHOT_MAP_PLACEHOLDER -->', '')
    if False:  # noqa - shot map WIP
        # Determine which direction team1 attacks in each half
        t1_p1_shots = [s for s in k_shots_xy if s.get('Period') == '1']
        has_period_data = any(s.get('Period') in ('1', '2') for s in k_shots_xy)
        attacks_low_x_p1 = True
        if t1_p1_shots:
            avg_x = sum(float(s['Location X']) for s in t1_p1_shots) / len(t1_p1_shots)
            attacks_low_x_p1 = avg_x < 0.5
        
        # To-scale SVG half-pitch (goal at top, halfway at bottom)
        # GAA pitch: 145m long, 85m wide. Half = 72.5m.
        PW = 85       # pitch width (metres)
        PH = 72.5     # half pitch length
        PAD = 4       # padding around pitch
        S = 8         # scale: 1m = 8 SVG units
        sw = PW * S
        sh = PH * S
        vb_w = sw + PAD * 2 * S
        vb_h = sh + PAD * 2 * S
        ox = PAD * S   # origin x offset
        oy = PAD * S   # origin y offset
        cx = PW / 2    # centre x in metres
        
        # Goal dimensions
        goal_w = 6.4
        goal_post_l = cx - goal_w / 2
        goal_post_r = cx + goal_w / 2
        
        # Small rectangle: 4.5m deep x 14m wide
        sm_w, sm_d = 14, 4.5
        sm_l = cx - sm_w / 2
        
        import math
        
        def m2svg(mx, my):
            """Convert metres (0,0 = top-left of pitch) to SVG coords."""
            return ox + mx * S, oy + my * S
        
        def build_pitch_svg():
            """Build a to-scale GAA half-pitch SVG with all markings."""
            lines = []
            lc = '#fff'   # line colour
            lw = 1.5      # line width
            
            # Pitch background
            px, py = m2svg(0, 0)
            lines.append(f'<rect x="{px}" y="{py}" width="{sw}" height="{sh}" fill="#2d8a4e" rx="4"/>')
            
            # Sidelines
            x0, y0 = m2svg(0, 0)
            x1, y1 = m2svg(0, PH)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}"/>')
            x0, y0 = m2svg(PW, 0)
            x1, y1 = m2svg(PW, PH)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}"/>')
            
            # End line (goal line)
            x0, y0 = m2svg(0, 0)
            x1, y1 = m2svg(PW, 0)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}"/>')
            
            # Halfway line
            x0, y0 = m2svg(0, PH)
            x1, y1 = m2svg(PW, PH)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}"/>')
            
            # Small rectangle
            sx, sy = m2svg(sm_l, 0)
            lines.append(f'<rect x="{sx}" y="{sy}" width="{sm_w * S}" height="{sm_d * S}" fill="none" stroke="{lc}" stroke-width="{lw}"/>')
            
            # 13m line (full width) with semicircular arc
            arc_r = 13 * S
            acx, acy = m2svg(cx, 0)
            ax0 = acx - arc_r
            ax1 = acx + arc_r
            lines.append(f'<path d="M {ax0} {acy} A {arc_r} {arc_r} 0 0 1 {ax1} {acy}" fill="none" stroke="{lc}" stroke-width="{lw}"/>')
            x0_13, y0_13 = m2svg(0, 13)
            x1_13, y1_13 = m2svg(PW, 13)
            lines.append(f'<line x1="{x0_13}" y1="{y0_13}" x2="{x1_13}" y2="{y1_13}" stroke="{lc}" stroke-width="{lw}"/>') 
            
            # 20m line
            x0, y0 = m2svg(0, 20)
            x1, y1 = m2svg(PW, 20)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}" stroke-dasharray="{S},{S*0.6}"/>')
            
            # 45m line
            x0, y0 = m2svg(0, 45)
            x1, y1 = m2svg(PW, 45)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}" stroke-dasharray="{S},{S*0.6}"/>')
            
            # 65m line
            x0, y0 = m2svg(0, 65)
            x1, y1 = m2svg(PW, 65)
            lines.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{lc}" stroke-width="{lw}" stroke-dasharray="{S},{S*0.6}"/>')
            
            # Goal posts and crossbar (behind the end line)
            gx0, gy = m2svg(goal_post_l, 0)
            gx1, _ = m2svg(goal_post_r, 0)
            goal_depth = 2 * S
            lines.append(f'<rect x="{gx0}" y="{gy - goal_depth}" width="{goal_w * S}" height="{goal_depth}" fill="none" stroke="{lc}" stroke-width="{lw + 0.5}"/>')
            
            # Line labels
            lbl_x, _ = m2svg(PW + 1.5, 0)
            for dist, label in [(20, '20m'), (45, '45m'), (65, '65m'), (PH, '½')]:
                _, ly = m2svg(0, dist)
                lines.append(f'<text x="{lbl_x}" y="{ly + 3}" font-size="9" fill="rgba(255,255,255,0.5)" font-family="sans-serif">{label}</text>')
            
            return '\n'.join(lines)
        
        def normalize_shot_for_team(e, is_team1):
            """Return (nx, ny) in 0..1 on the full pitch, all shots normalized
            to attack toward nx=0 (goal at top)."""
            x = float(e['Location X'])
            y = float(e['Location Y'])
            period = e.get('Period', '')
            
            if not has_period_data:
                return 1 - x, y
            
            if is_team1:
                if (period == '1' and attacks_low_x_p1) or (period == '2' and not attacks_low_x_p1):
                    return x, y
                else:
                    return 1 - x, 1 - y
            else:
                if (period == '1' and not attacks_low_x_p1) or (period == '2' and attacks_low_x_p1):
                    return x, y
                else:
                    return 1 - x, 1 - y
        
        def make_dot(sx, sy, outcome, player, name, period):
            cmap = {'Point': '#ffffff', 'Goal': '#ffff00', '2 Points': '#f39c12', 'Wide': '#e74c3c', 'Short': '#e67e22', 'Blocked': '#aaa', 'Save': '#aaa'}
            color = cmap.get(outcome, '#aaa')
            half_label = '1st' if period == '1' else '2nd'
            label = f"{player}: {outcome} ({half_label} half)" + (" (free)" if name == 'Scoreable free' else "")
            is_second_half = period == '2'
            opacity = '0.6' if is_second_half else '0.95'
            dash = ' stroke-dasharray="3,2"' if is_second_half else ''
            scored = outcome in ['Point', 'Goal', '2 Points']
            if scored:
                r = 2.2 if outcome == 'Goal' else 1.6
                return f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r * S}" fill="{color}" opacity="{opacity}" stroke="#333" stroke-width="1.5"{dash}><title>{label}</title></circle>'
            else:
                s = 1.2 * S
                return f'<g opacity="{opacity}"><line x1="{sx-s:.1f}" y1="{sy-s:.1f}" x2="{sx+s:.1f}" y2="{sy+s:.1f}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"{dash}/><line x1="{sx+s:.1f}" y1="{sy-s:.1f}" x2="{sx-s:.1f}" y2="{sy+s:.1f}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"{dash}/><title>{label}</title></g>'
        
        pitch_markings = build_pitch_svg()
        
        # Legend
        leg_y = vb_h - PAD * S * 0.4
        leg_cx = vb_w / 2
        legend = f'<g transform="translate({leg_cx - 200},{leg_y})" font-family="sans-serif">'
        legend += f'<circle cx="0" cy="0" r="5" fill="#fff" stroke="#333" stroke-width="1"/><text x="8" y="4" font-size="9" fill="#888">Point</text>'
        legend += f'<circle cx="60" cy="0" r="5" fill="#ffff00" stroke="#333" stroke-width="1"/><text x="68" y="4" font-size="9" fill="#888">Goal</text>'
        legend += f'<circle cx="115" cy="0" r="5" fill="#f39c12" stroke="#333" stroke-width="1"/><text x="123" y="4" font-size="9" fill="#888">2pt</text>'
        legend += f'<g opacity="0.85"><line x1="162" y1="-4" x2="170" y2="4" stroke="#e74c3c" stroke-width="2" stroke-linecap="round"/><line x1="170" y1="-4" x2="162" y2="4" stroke="#e74c3c" stroke-width="2" stroke-linecap="round"/></g><text x="175" y="4" font-size="9" fill="#888">Wide</text>'
        legend += f'<g opacity="0.85"><line x1="212" y1="-4" x2="220" y2="4" stroke="#e67e22" stroke-width="2" stroke-linecap="round"/><line x1="220" y1="-4" x2="212" y2="4" stroke="#e67e22" stroke-width="2" stroke-linecap="round"/></g><text x="225" y="4" font-size="9" fill="#888">Short</text>'
        legend += f'<circle cx="272" cy="0" r="5" fill="#fff" stroke="#333" stroke-width="1"/><text x="280" y="4" font-size="9" fill="#888">1st Half</text>'
        legend += f'<circle cx="340" cy="0" r="5" fill="#fff" stroke="#333" stroke-width="1" stroke-dasharray="2,1.5" opacity="0.6"/><text x="348" y="4" font-size="9" fill="#888">2nd Half</text>'
        legend += '</g>'
        
        def build_shot_map_svg(shots, team_name, is_team1):
            dots = ''
            for e in shots:
                nx, ny = normalize_shot_for_team(e, is_team1)
                # nx: 0=goal end, 1=far end. ny: 0..1 across width
                # Convert to metres on half pitch then to SVG
                my = nx * 145       # metres from goal end (full pitch)
                mx = ny * PW        # metres across pitch
                if my > PH + PAD:   # skip shots beyond halfway + padding
                    continue
                sx, sy = m2svg(mx, my)
                dots += make_dot(sx, sy, e['Outcome'], e.get('Player', ''), e.get('Name', ''), e.get('Period', '1'))
            return f"""<svg viewBox="0 0 {vb_w} {vb_h}" style="width:100%;height:auto;max-width:500px">
                        {pitch_markings}
                        {dots}
                        {legend}
                    </svg>"""
        
        t1_svg = build_shot_map_svg(k_shots_xy, stats['team1'], True) if k_shots_xy else ''
        t2_svg = build_shot_map_svg(o_shots_xy, stats['team2'], False) if o_shots_xy else ''
        
        shot_map_html = ''
        if t1_svg:
            shot_map_html += f"""\n            <div class="chart-container" style="margin: 30px 0;">
                <div class="chart-title">\U0001f5fa\ufe0f Shot Map \u2014 {stats['team1']}</div>
                <div style="text-align:center;margin-bottom:8px;font-size:.85em;color:#7f8c8d">Hover for player & outcome details</div>
                <div style="max-width:800px;margin:0 auto">{t1_svg}</div>
            </div>\n"""
        if t2_svg:
            shot_map_html += f"""\n            <div class="chart-container" style="margin: 30px 0;">
                <div class="chart-title">\U0001f5fa\ufe0f Shot Map \u2014 {stats['team2']}</div>
                <div style="text-align:center;margin-bottom:8px;font-size:.85em;color:#7f8c8d">Hover for player & outcome details</div>
                <div style="max-width:800px;margin:0 auto">{t2_svg}</div>
            </div>\n"""
        
        html = html.replace('<!-- SHOT_MAP_PLACEHOLDER -->', shot_map_html)

    # Replace attacks stats
    html = html.replace('ATTACKS_WITH_SHOT / TOTAL_ATTACKS', f'{attacks_with_shot_2026} / {total_attacks_2026}')
    html = html.replace('TOTAL_ATTACKS', str(stats['t1_attacks']))
    html = re.sub(r'<div class="bar bar-killinkere" style="width: calc\(29 \* 3%\)">29 / 18 \(62%\)</div>',
                  f'<div class="bar bar-killinkere" style="width: calc({stats["t1_attacks"]} * 3%)">{stats["t1_attacks"]} / {stats["t1_attacks_shot"]} ({attacks_pct}%)</div>', html)
    
    # Replace frees conceded by zone
    html = html.replace('TEAM_NAME_PLACEHOLDER', stats['team1'])
    html = html.replace('ATTACKING_FREES', str(stats['t1_frees_attacking']))
    html = html.replace('MIDDLE_FREES', str(stats['t1_frees_middle']))
    html = html.replace('DEFENSIVE_FREES', str(stats['t1_frees_defensive']))
    
    # Replace period stats - overall accuracy
    html = html.replace('<strong>Killinkere:</strong> 58%', f'<strong>{stats["team1"]}:</strong> {stats["t1_acc"]}%')
    html = html.replace('<strong>Aughadrumsee:</strong> 50%', f'<strong>{stats["team2"]}:</strong> {stats["t2_acc"]}%')
    
    html = re.sub(r'<strong>3-5 \(14 pts\)</strong>',
                  f'<strong>{stats["t1_p1_goals"]}-{stats["t1_p1_points"]+stats["t1_p1_two_pts"]*2} ({stats["t1_p1_total"]} pts)</strong>', html, count=1)
    html = re.sub(r'(<div class="period-title">⏱️ 1ST HALF</div>.*?<span>'+re.escape(stats['team2'])+r' Score:</span>\s*)<strong>0-7 \(7 pts\)</strong>',
                  f'\\1<strong>{stats["t2_p1_goals"]}-{stats["t2_p1_points"]+stats["t2_p1_two_pts"]*2} ({stats["t2_p1_total"]} pts)</strong>', html, count=1, flags=re.DOTALL)
    html = re.sub(r'<strong>1-4 \(7 pts\)</strong>',
                  f'<strong>{stats["t1_p2_goals"]}-{stats["t1_p2_points"]+stats["t1_p2_two_pts"]*2} ({stats["t1_p2_total"]} pts)</strong>', html, count=1)
    html = re.sub(r'(<div class="period-title">⏱️ 2ND HALF</div>.*?<span>'+re.escape(stats['team2'])+r' Score:</span>\s*)<strong>0-5 \(5 pts\)</strong>',
                  f'\\1<strong>{stats["t2_p2_goals"]}-{stats["t2_p2_points"]+stats["t2_p2_two_pts"]*2} ({stats["t2_p2_total"]} pts)</strong>', html, count=1, flags=re.DOTALL)
    
    # Replace period shot stats
    html = re.sub(r'<strong>5/8 \(62\.5% accuracy\)</strong>',
                  f'<strong>{stats["t1_p1_shots_scored"]}/{stats["t1_p1_shots_total"]} ({stats["t1_p1_acc"]}% accuracy)</strong>', html, count=1)
    html = re.sub(r'<strong>7/11 \(63\.6% accuracy\)</strong>',
                  f'<strong>{stats["t2_p1_shots_scored"]}/{stats["t2_p1_shots_total"]} ({stats["t2_p1_acc"]}% accuracy)</strong>', html, count=1)
    html = re.sub(r'<strong>6/11 \(54\.5% accuracy\)</strong>',
                  f'<strong>{stats["t1_p2_shots_scored"]}/{stats["t1_p2_shots_total"]} ({stats["t1_p2_acc"]}% accuracy)</strong>', html, count=1)
    html = re.sub(r'<strong>2/7 \(28\.6% accuracy\)</strong>',
                  f'<strong>{stats["t2_p2_shots_scored"]}/{stats["t2_p2_shots_total"]} ({stats["t2_p2_acc"]}% accuracy)</strong>', html, count=1)
    
    # Replace chart data
    html = re.sub(r"data: \[4, 7, 1, 21\]",
                  f"data: [{stats['t1_goals']}, {stats['t1_points']}, {stats['t1_two_pts']}, {stats['t1_total_score']}]", html, count=1)
    html = re.sub(r"data: \[0, 12, 0, 12\]",
                  f"data: [{stats['t2_goals']}, {stats['t2_points']}, {stats['t2_two_pts']}, {stats['t2_total_score']}]", html, count=1)
    
    # Generate timeline chart data (scores only, exclude bookings)
    timeline = stats['timeline']
    score_timeline = [e for e in timeline if not e.get('is_booking')]
    labels = ['Start'] + [e['time'] for e in score_timeline] + ['FT']
    t1_data = [0] + [e['t1_score'] for e in score_timeline] + [score_timeline[-1]['t1_score'] if score_timeline else 0]
    t2_data = [0] + [e['t2_score'] for e in score_timeline] + [score_timeline[-1]['t2_score'] if score_timeline else 0]
    
    # Generate point styles and colors dynamically based on actual events
    t1_point_styles = ['circle']  # Start
    t1_point_colors = ['']  
    t2_point_styles = ['circle']
    t2_point_colors = ['']
    
    for e in score_timeline:
        if e['team'] == stats['team1']:
            if e['outcome'] == 'Goal':
                t1_point_styles.append('rectRot')
                t1_point_colors.append('green')
            elif e['outcome'] == '2 Points':
                t1_point_styles.append('rectRot')
                t1_point_colors.append('orange')
            else:  # Regular Point
                t1_point_styles.append('circle')
                t1_point_colors.append('white')
            # Opposition doesn't score, so no visible marker
            t2_point_styles.append('circle')
            t2_point_colors.append('')
        else:
            # Opposition scores
            if e['outcome'] == 'Goal':
                t2_point_styles.append('rectRot')
                t2_point_colors.append('red')
            elif e['outcome'] == '2 Points':
                t2_point_styles.append('rectRot')
                t2_point_colors.append('orange')
            else:  # Regular Point
                t2_point_styles.append('circle')
                t2_point_colors.append('white')
            # Killinkere doesn't score, so no visible marker
            t1_point_styles.append('circle')
            t1_point_colors.append('')
    
    t1_point_styles.append('circle')  # FT
    t1_point_colors.append('')
    t2_point_styles.append('circle')
    t2_point_colors.append('')
    
    # Generate point radius array (larger for first score after HT)
    t1_point_radius = [7]  # Start
    for i, e in enumerate(score_timeline):
        is_first_after_ht = (e['period'] == '2' and i == 0) or (i > 0 and score_timeline[i-1]['period'] == '1' and e['period'] == '2')
        is_first_after_ht = is_first_after_ht and e['team'] == stats['team1']
        
        if e['team'] == stats['team1']:
            t1_point_radius.append(12 if is_first_after_ht else 7)
        else:
            t1_point_radius.append(7)
    t1_point_radius.append(7)  # FT
    
    # Generate tooltip labels array
    t1_tooltip_labels = ['']
    for e in score_timeline:
        if e['team'] == stats['team1']:
            if e['outcome'] == 'Goal':
                t1_tooltip_labels.append('Goal')
            elif e['outcome'] == '2 Points':
                t1_tooltip_labels.append('2pts')
            else:
                t1_tooltip_labels.append('1pt')
        else:
            t1_tooltip_labels.append('')
    t1_tooltip_labels.append('')  # FT
    
    # Replace hardcoded point styles and colors with dynamic ones
    # Replace the [0] placeholder arrays with actual data
    html = html.replace(
        "pointRadius: [0],",
        f"pointRadius: {t1_point_radius},",
        1
    )
    
    html = html.replace(
        "const scoreTypes = [0];",
        f"const scoreTypes = {t1_point_styles};",
        1
    )
    
    html = html.replace(
        "const scoreTypes = [0];",
        f"const scoreTypes = {t1_point_colors};",
        1
    )
    
    html = html.replace(
        "const scoreTypes = [0];",
        f"const scoreTypes = {t2_point_styles};",
        1
    )
    
    html = html.replace(
        "const scoreTypes = [0];",
        f"const scoreTypes = {t2_point_colors};",
        1
    )
    
    html = html.replace(
        "const scoreTypes = [0];",
        f"const scoreTypes = {t1_tooltip_labels};",
        1
    )
    
    # Find halftime position
    ht_index = len([e for e in score_timeline if e['period'] == '1'])
    
    # Replace timeline chart data
    old_labels_pattern = r"labels: \['Start'[^\]]+\]"
    new_labels = f"labels: {labels}"
    html = re.sub(old_labels_pattern, new_labels, html)
    
    # Update halftime index dynamically
    html = re.sub(r'const htIndex = 13;', f'const htIndex = {ht_index};', html)
    
    # Replace chart data - use generic pattern that works for any team name
    # First occurrence is Killinkere
    html = html.replace("                    label: 'Killinkere',\n                    data: [0],", 
                        f"                    label: '{stats['team1']}',\n                    data: {t1_data},", 1)
    # Second occurrence is the opposition team (find and replace the [0] after Killinkere)
    html = re.sub(r"(}, \{\s*label: '[^']+',\s*data: )\[0\],", 
                  f"\\1{t2_data},", html, count=1)
    
    # Replace 2026 accuracy in targets tab
    html = html.replace('YEAR_2026_ACCURACY', str(year_2026_accuracy))
    html = html.replace('ATTACKS_2026_PCT', str(attacks_2026_pct))
    html = html.replace('GOALS_2026', str(goals_2026))
    html = html.replace('TWO_POINTERS_2026', str(two_pointers_2026))
    html = html.replace('POINTS_2026', str(points_2026))
    
    # Inject per-game accumulative data for targets charts
    html = html.replace('GAME_LABELS_JSON', str(game_labels))
    html = html.replace('GAME_COMPETITIONS_JSON', str(game_competitions))
    html = html.replace('ACC_ACCURACY_JSON', str(acc_accuracy))
    html = html.replace('PER_GAME_ACCURACY_JSON', str(per_game_accuracy))
    html = html.replace('ACC_GOALS_JSON', str(acc_goals))
    html = html.replace('ACC_TWO_PTS_JSON', str(acc_two_pts))
    html = html.replace('ACC_POINTS_JSON', str(acc_points))
    html = html.replace('ACC_ATTACK_PCT_JSON', str(acc_attack_pct))
    html = html.replace('PER_GAME_ATTACK_PCT_JSON', str(per_game_attack_pct))
    
    # Replace scoreable frees - using unique placeholders, MUST be after all regex replacements
    html = html.replace('SF_TOTAL_T1', str(stats['t1_sf_total']))
    html = html.replace('SF_TOTAL_T2', str(stats['t2_sf_total']))
    html = html.replace('SF_GOALS_T1', str(stats['t1_sf_goals']))
    html = html.replace('SF_GOALS_T2', str(stats['t2_sf_goals']))
    html = html.replace('SF_TWO_PTS_T1', str(stats['t1_sf_two_pts']))
    html = html.replace('SF_TWO_PTS_T2', str(stats['t2_sf_two_pts']))
    html = html.replace('SF_POINTS_T1', str(stats['t1_sf_points']))
    html = html.replace('SF_POINTS_T2', str(stats['t2_sf_points']))
    html = html.replace('SF_WIDES_T1', str(stats['t1_sf_wides']))
    html = html.replace('SF_WIDES_T2', str(stats['t2_sf_wides']))
    html = html.replace('SF_SHORTS_T1', str(stats['t1_sf_shorts']))
    html = html.replace('SF_SHORTS_T2', str(stats['t2_sf_shorts']))
    html = html.replace('SF_ACC_T1', str(stats['t1_sf_acc']))
    html = html.replace('SF_ACC_T2', str(stats['t2_sf_acc']))
    
    # Replace 45s
    html = html.replace('FORTYFIVES_T1', str(stats['t1_45s']))
    html = html.replace('FORTYFIVES_T2', str(stats['t2_45s']))
    
    # Replace scoreable frees from 45s
    html = html.replace('SF45_SCORED_T1', str(stats['t1_sf45_scored']))
    html = html.replace('SF45_TOTAL_T1', str(stats['t1_sf45_total']))
    html = html.replace('SF45_SCORED_T2', str(stats['t2_sf45_scored']))
    html = html.replace('SF45_TOTAL_T2', str(stats['t2_sf45_total']))
    
    # Replace score breakdown - scored from frees and 45s
    html = html.replace('PTS_FROM_FOULS_T1', str(stats['t1_pts_from_fouls']))
    html = html.replace('PTS_FROM_FOULS_T2', str(stats['t2_pts_from_fouls']))
    html = html.replace('PTS_FROM_45S_T1', str(stats['t1_pts_from_45s']))
    html = html.replace('PTS_FROM_45S_T2', str(stats['t2_pts_from_45s']))
    
    # Generate timeline HTML
    timeline_html = ''
    for i, e in enumerate(timeline):
        team_class = 'killinkere' if e['team'] == stats['team1'] else 'aughadrumsee'
        player_name = f"<strong>{e['player']}</strong>" if e['player'] else stats['team1'] if e['team'] == stats['team1'] else stats['team2']
        
        # Handle bookings
        if e.get('is_booking'):
            card_type = e['outcome']
            if card_type == 'Yellow':
                icon = '🟨'
                desc = f"{player_name} — Yellow Card"
            elif card_type == 'Black':
                icon = '⬛'
                desc = f"{player_name} — Black Card (Sin Bin)"
            else:
                icon = '🟥'
                desc = f"{player_name} — Red Card"
            desc += f" ({e['team']})"
            score_text = f"{e['t1_score']} vs {e['t2_score']}"
            timeline_html += f'''                <div class="timeline-event {team_class}" style="border-left-color: #e74c3c;">
                    <span class="timeline-time">{e['time']}</span>
                    <span class="timeline-icon">{icon}</span>
                    <span class="timeline-desc">{desc} <span style="color: #95a5a6; font-weight: normal;">({score_text})</span></span>
                </div>
'''
            continue
        
        icon = '🥅' if e['outcome'] == 'Goal' else ('🏐🏐' if e['outcome'] == '2 Points' else '🏐')
        
        # Check if this is first score after halftime by team1
        is_first_after_ht = (e['period'] == '2' and i == 0) or (i > 0 and timeline[i-1]['period'] == '1' and e['period'] == '2')
        is_first_after_ht = is_first_after_ht and e['team'] == stats['team1']
        
        if e['outcome'] == 'Goal':
            desc = f"GOAL! {player_name}"
        elif e['outcome'] == '2 Points':
            desc = f"{player_name} scores 2 points!"
        else:
            desc = f"{player_name} scores point"
        
        if e['name'] == 'Scoreable free':
            desc += ' from free'
        
        desc += f" for {e['team']}"
        
        if is_first_after_ht:
            desc += " 🎯 <strong style='color: #f39c12;'>FIRST SCORE AFTER HALFTIME!</strong>"
        
        score_text = f"({e['t1_score']} vs {e['t2_score']})"
        # Check if this is the last event of period 1
        is_ht = e['period'] == '1' and (e == timeline[-1] or (timeline.index(e) < len(timeline) - 1 and timeline[timeline.index(e) + 1]['period'] == '2'))
        if is_ht:
            score_text += ' at HT'
        elif e == timeline[-1]:
            score_text += ' FT'
        
        timeline_html += f'''                <div class="timeline-event {team_class}">
                    <span class="timeline-time">{e['time']}</span>
                    <span class="timeline-icon">{icon}</span>
                    <span class="timeline-desc">{desc} <span style="color: #95a5a6; font-weight: normal;">({score_text})</span></span>
                </div>
'''
    
    # Add halftime divider after last period 1 event
    p1_events = [e for e in timeline if e['period'] == '1']
    if p1_events:
        last_p1_idx = timeline.index(p1_events[-1])
        timeline_parts = timeline_html.split('</div>\n')
        ht_divider = '''                <div style="text-align: center; padding: 20px; margin: 20px 0; background: linear-gradient(90deg, rgba(0,0,0,0.05), rgba(0,0,0,0.1), rgba(0,0,0,0.05)); border-top: 2px dashed rgba(0,0,0,0.3); border-bottom: 2px dashed rgba(0,0,0,0.3);">
                    <span style="font-size: 1.3em; font-weight: bold; color: #2c3e50;">⏱️ HALF TIME ⏱️</span>
                </div>
'''
        timeline_html = '</div>\n'.join(timeline_parts[:last_p1_idx+1]) + '</div>\n' + ht_divider + '</div>\n'.join(timeline_parts[last_p1_idx+1:])
    
    # Replace timeline section
    timeline_pattern = r'(<div class="timeline">).*?(</div>\s*</div>\s*</div>\s*<script>)'
    timeline_replacement = f"\\1\n{timeline_html}            \\2"
    html = re.sub(timeline_pattern, timeline_replacement, html, flags=re.DOTALL)
    
    # Generate player tables HTML
    def generate_player_table(players, team_name, color):
        def gaa_notation(data):
            parts = []
            if data['free_goals'] > 0:  parts.append(f"{data['free_goals']}gf")
            if data['free_points'] > 0: parts.append(f"{data['free_points']}f")
            play_two = data['two_pts'] - data['free_two_pts']
            if play_two > 0:            parts.append(f"{play_two}x2pt")
            if data['free_two_pts'] > 0: parts.append(f"{data['free_two_pts']}x2ptf")
            base = f"{data['goals']}-{data['points'] + data['two_pts'] * 2}"
            if parts:
                qualifier = ', '.join(parts)
                return f'{base} <span style="color:#888">({qualifier})</span>'
            return base
        
        rows = ''
        for name, data in players:
            total_score = data['goals'] * 3 + data['points'] + data['two_pts'] * 2
            total_attempts = data['shots'] + data['free_attempts']
            total_scored = data['scored'] + data['frees_scored']
            acc = round((total_scored / total_attempts * 100)) if total_attempts > 0 else 0
            acc_display = f"{acc}%" if total_attempts > 0 else "-"
            bg_style = f"background: linear-gradient(90deg, {color[0]}, {color[1]});" if color else ""
            
            rows += f'''                    <tr>
                        <td><strong>{name}</strong></td>
                        <td>{data['goals']}</td>
                        <td>{data['two_pts']}</td>
                        <td>{data['points']}</td>
                        <td>{gaa_notation(data)}</td>
                        <td>{total_attempts}</td>
                        <td>
                            <div class="accuracy-bar">
                                <div class="accuracy-fill" style="width: {acc}%; {bg_style}">{acc_display}</div>
                            </div>
                        </td>
                        <td>{data['turnovers']}</td>
                        <td>{data['poss_lost']}</td>
                        <td>{data['frees']}</td>
                        <td>{data['kickouts']}</td>
                    </tr>
'''
        return rows
    
    t1_table = generate_player_table(stats['t1_players'], stats['team1'], ('#27ae60', '#2ecc71'))
    t2_table = generate_player_table(stats['t2_players'], stats['team2'], ('#c0392b', '#e74c3c'))
    
    # Replace player tables
    t1_table_pattern = r'(<h2 style="color: #2ecc71[^>]+>🟢 ' + re.escape(stats['team1']) + r' Top Performers</h2>.*?<table class="player-table">\s*<thead>.*?</thead>\s*<tbody>).*?(</tbody>\s*</table>)'
    t1_table_replacement = f"\\1\n{t1_table}                \\2"
    html = re.sub(t1_table_pattern, t1_table_replacement, html, flags=re.DOTALL)
    
    t2_table_pattern = r'(<h2 style="color: #e74c3c[^>]+>🔴 ' + re.escape(stats['team2']) + r' Top Performers</h2>.*?<table class="player-table">\s*<thead>.*?</thead>\s*<tbody>).*?(</tbody>\s*</table>)'
    t2_table_replacement = f"\\1\n{t2_table}                \\2"
    html = re.sub(t2_table_pattern, t2_table_replacement, html, flags=re.DOTALL)
    
    # Output file
    output_file = csv_file.replace('.csv', '_FULL_infographic.html')
    
    print(f"💾 Writing: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ SUCCESS! Generated: {output_file}")
    print(f"{'='*60}\n")
    
    return output_file

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 full_auto_generator.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    generate_html(csv_file)
