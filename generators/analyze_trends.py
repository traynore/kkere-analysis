#!/usr/bin/env python3
"""Analyze trends across all 4 games"""

import csv
from pathlib import Path
from collections import defaultdict

games = [
    "Killinkere 1 - 14 v 1 - 12 Clones.csv",
    "Killinkere 3 - 11 v 1 - 13 Denn.csv", 
    "Killinkere 3 - 14 v 1 - 10 Pearse OG.csv",
    "Killinkere 4 - 9 v 0 - 12 Aughadrumsee.csv"
]

print("="*70)
print("KILLINKERE PERFORMANCE TRENDS - 4 GAME ANALYSIS")
print("="*70)

results = []
for game_file in games:
    events = []
    with open(game_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Team Name'):
                events.append(row)
    
    # Get opponent name
    teams = set(e['Team Name'] for e in events if e.get('Team Name'))
    opponent = [t for t in teams if t != 'Killinkere'][0]
    
    # Killinkere stats
    k_events = [e for e in events if e['Team Name'] == 'Killinkere']
    k_shots = [e for e in k_events if e.get('Name') == 'Shot from play']
    k_scored = len([s for s in k_shots if s['Outcome'] in ['Goal', 'Point', '2 Points']])
    k_goals = len([s for s in k_shots if s['Outcome'] == 'Goal'])
    k_points = len([s for s in k_shots if s['Outcome'] == 'Point'])
    k_two_pts = len([s for s in k_shots if s['Outcome'] == '2 Points'])
    k_wides = len([s for s in k_shots if s['Outcome'] == 'Wide'])
    k_total_score = k_goals * 3 + k_points + k_two_pts * 2
    k_acc = round(k_scored / len(k_shots) * 100, 1) if k_shots else 0
    
    # Kickouts
    k_kickouts = [e for e in k_events if e.get('Name') == 'Kickout']
    k_ko_won = len([k for k in k_kickouts if k['Outcome'] in ['Won clean', 'Short won', 'Break won']])
    k_ko_pct = round(k_ko_won / len(k_kickouts) * 100) if k_kickouts else 0
    
    # Turnovers & Frees
    k_turnovers = len([e for e in k_events if e.get('Name') == 'Turnover'])
    k_frees = len([e for e in k_events if e.get('Name') == 'Free conceded'])
    
    # First score after HT
    scoring = [e for e in events if e.get('Name') in ['Shot from play', 'Scoreable free'] 
               and e.get('Outcome') in ['Goal', 'Point', '2 Points']]
    scoring.sort(key=lambda x: (int(x.get('Period', '1')), x.get('Time', '')))
    p2_scores = [e for e in scoring if e['Period'] == '2']
    first_after_ht = p2_scores[0]['Team Name'] == 'Killinkere' if p2_scores else False
    
    # Result
    opp_events = [e for e in events if e['Team Name'] == opponent]
    opp_shots = [e for e in opp_events if e.get('Name') == 'Shot from play']
    opp_scored = len([s for s in opp_shots if s['Outcome'] in ['Goal', 'Point', '2 Points']])
    opp_goals = len([s for s in opp_shots if s['Outcome'] == 'Goal'])
    opp_points = len([s for s in opp_shots if s['Outcome'] == 'Point'])
    opp_two_pts = len([s for s in opp_shots if s['Outcome'] == '2 Points'])
    opp_total = opp_goals * 3 + opp_points + opp_two_pts * 2
    
    result = "WIN" if k_total_score > opp_total else "LOSS"
    margin = k_total_score - opp_total
    
    results.append({
        'opponent': opponent,
        'result': result,
        'margin': margin,
        'k_score': k_total_score,
        'opp_score': opp_total,
        'k_acc': k_acc,
        'k_shots': len(k_shots),
        'k_scored': k_scored,
        'k_wides': k_wides,
        'k_ko_pct': k_ko_pct,
        'k_turnovers': k_turnovers,
        'k_frees': k_frees,
        'first_ht': first_after_ht
    })

# Summary
wins = len([r for r in results if r['result'] == 'WIN'])
losses = len([r for r in results if r['result'] == 'LOSS'])

print(f"\n📊 RECORD: {wins} Wins - {losses} Losses")
print(f"Average Margin: {sum(r['margin'] for r in results) / len(results):+.1f} points")
print(f"Average Score: {sum(r['k_score'] for r in results) / len(results):.1f} points")

print("\n🎯 SHOOTING ACCURACY TRENDS:")
print(f"Average Accuracy: {sum(r['k_acc'] for r in results) / len(results):.1f}%")
print(f"Best: {max(r['k_acc'] for r in results):.1f}% | Worst: {min(r['k_acc'] for r in results):.1f}%")
print(f"Average Wides per game: {sum(r['k_wides'] for r in results) / len(results):.1f}")

print("\n🏐 KICKOUT SUCCESS:")
print(f"Average: {sum(r['k_ko_pct'] for r in results) / len(results):.0f}%")
print(f"Best: {max(r['k_ko_pct'] for r in results)}% | Worst: {min(r['k_ko_pct'] for r in results)}%")

print("\n⚠️ DISCIPLINE & POSSESSION:")
print(f"Average Turnovers: {sum(r['k_turnovers'] for r in results) / len(results):.1f}")
print(f"Average Frees Conceded: {sum(r['k_frees'] for r in results) / len(results):.1f}")

print("\n🎯 FIRST SCORE AFTER HALFTIME:")
scored_first = len([r for r in results if r['first_ht']])
print(f"Scored first: {scored_first}/4 games ({scored_first/4*100:.0f}%)")

print("\n" + "="*70)
print("KEY INSIGHTS:")
print("="*70)

# Accuracy correlation
high_acc_games = [r for r in results if r['k_acc'] > 55]
high_acc_wins = len([r for r in high_acc_games if r['result'] == 'WIN'])
print(f"\n✓ When accuracy > 55%: {high_acc_wins}/{len(high_acc_games)} wins")

# Kickout correlation
high_ko_games = [r for r in results if r['k_ko_pct'] > 70]
high_ko_wins = len([r for r in high_ko_games if r['result'] == 'WIN'])
print(f"✓ When kickout success > 70%: {high_ko_wins}/{len(high_ko_games)} wins")

# Turnovers
low_to_games = [r for r in results if r['k_turnovers'] < 10]
low_to_wins = len([r for r in low_to_games if r['result'] == 'WIN'])
print(f"✓ When turnovers < 10: {low_to_wins}/{len(low_to_games)} wins")

print("\n🔴 AREAS FOR IMPROVEMENT:")
if sum(r['k_wides'] for r in results) / len(results) > 5:
    print(f"  • Wide count averaging {sum(r['k_wides'] for r in results) / len(results):.1f} - focus on shot selection")
if sum(r['k_acc'] for r in results) / len(results) < 60:
    print(f"  • Accuracy at {sum(r['k_acc'] for r in results) / len(results):.1f}% - target 70%+")
if scored_first < 3:
    print(f"  • Only scored first after HT in {scored_first}/4 games - work on second half starts")

print("\n🟢 STRENGTHS:")
if sum(r['k_ko_pct'] for r in results) / len(results) > 70:
    print(f"  • Strong kickout retention at {sum(r['k_ko_pct'] for r in results) / len(results):.0f}%")
if wins >= 3:
    print(f"  • Excellent win rate: {wins}/4 games")
if sum(r['k_score'] for r in results) / len(results) > 18:
    print(f"  • High scoring output: {sum(r['k_score'] for r in results) / len(results):.1f} points per game")

print("\n" + "="*70)
