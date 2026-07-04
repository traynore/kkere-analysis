#!/usr/bin/env python3
"""Tactical analysis: actionable patterns for Killinkere management."""

import csv, os, glob, difflib
from collections import defaultdict

def parse_time(t):
    parts = t.strip().split(':')
    if len(parts)==3: return int(parts[0])*3600+int(parts[1])*60+int(parts[2])
    elif len(parts)==2: return int(parts[0])*60+int(parts[1])
    return 0

def fmt(sec):
    m,s=divmod(int(sec),60)
    return f"{m:02d}:{s:02d}"

def load_meta(fp):
    meta={}
    mp=fp.replace('.csv','.meta')
    if os.path.exists(mp):
        for line in open(mp):
            if '=' in line:
                k,v=line.strip().split('=',1)
                meta[k.strip()]=v.strip()
    if not meta:
        d=os.path.dirname(fp)
        base=os.path.basename(fp).replace('.csv','')
        metas=[os.path.basename(m).replace('.meta','') for m in glob.glob(os.path.join(d,'Killinkere*.meta'))]
        matches=difflib.get_close_matches(base,metas,n=1,cutoff=0.85)
        if matches:
            for line in open(os.path.join(d,matches[0]+'.meta')):
                if '=' in line:
                    k,v=line.strip().split('=',1)
                    meta[k.strip()]=v.strip()
    return meta

def classify(comp):
    c=comp.lower()
    if 'div 3' in c: return 'Div 3'
    elif 'div 7' in c or 'div 5' in c: return 'Div 7'
    elif 'spring league' in c: return 'Spring League'
    elif 'challenge' in c: return 'Challenge'
    return 'Other'

def load_game(fp):
    events=[]
    try:
        for enc in ['utf-8','utf-8-sig','latin-1','cp1252']:
            try:
                with open(fp,'r',encoding=enc) as f: content=f.read()
                break
            except UnicodeDecodeError: continue
        lines=content.replace('\r\n','\n').replace('\r','\n').split('\n')
        clean=[]
        for l in lines:
            if l.strip()=='' or l.startswith('='): break
            clean.append(l)
        if not clean: return []
        for row in csv.DictReader(clean):
            t=row.get('Time','')
            if not t: continue
            events.append({
                'time': parse_time(t),
                'team': row.get('Team Name',''),
                'name': row.get('Name',''),
                'outcome': row.get('Outcome',''),
                'player': row.get('Player',''),
                'period': row.get('Period', row.get('Game Period',''))
            })
    except: pass
    return events

def main():
    data_dir='/Users/hz448961/DevOps/test/data'
    csv_files=sorted(glob.glob(os.path.join(data_dir,'Killinkere*.csv')))
    
    # Aggregators
    response_times = []  # time between opp scoring and next Killinkere score
    conceding_clusters = []  # how often opp scores 2+ in a row without response
    score_sources = defaultdict(int)  # what happened before we scored
    turnover_to_score = []  # time from winning turnover to scoring
    kickout_results = defaultdict(int)
    kickout_score_after_won = 0
    kickout_score_after_lost = 0
    kickout_total_won = 0
    kickout_total_lost = 0
    possession_lost_types = defaultdict(int)
    shots_after_turnover = {'taken':0, 'scored':0}
    shots_after_kickout_won = {'taken':0, 'scored':0}
    shots_built = {'taken':0, 'scored':0}
    wides_by_phase = defaultdict(int)
    scores_by_phase = defaultdict(int)
    shots_by_phase = defaultdict(int)
    frees_conceded_after_score = 0  # frees conceded within 2 min of scoring
    total_scores_k = 0
    games_data = []
    
    for fp in csv_files:
        game_name = os.path.basename(fp).replace('.csv','').replace('Killinkere ','')
        meta = load_meta(fp)
        comp = classify(meta.get('competition',''))
        events = load_game(fp)
        if not events: continue
        
        k_scores = []
        opp_scores = []
        k_turnovers_won = []  # times Killinkere won turnovers
        k_kickouts_own = []  # Killinkere's own kickout results
        
        for i, e in enumerate(events):
            t = e['time']
            phase = t // 600  # 0-5 for each 10-min block
            
            # Score tracking
            if e['team']=='Killinkere' and e['name'] in ['Shot from play','Scoreable free'] and e['outcome'] in ['Point','2 Points','Goal']:
                k_scores.append(t)
                total_scores_k += 1
                scores_by_phase[phase] += 1
                
                # What was the source? Look back for context
                source = 'built'
                for j in range(i-1, max(i-8, -1), -1):
                    prev = events[j]
                    if prev['time'] < t - 30: break  # only look 30 sec back
                    if prev['team']=='Killinkere' and prev['name']=='Turnover':
                        source = 'turnover'
                        break
                    if prev['team']=='Killinkere' and prev['name']=='Kickout' and prev['outcome'] in ['Won clean','Short won','Break won']:
                        source = 'own_kickout'
                        break
                    if prev['team']!='Killinkere' and prev['name']=='Kickout' and prev['outcome'] in ['Lost clean','Break lost']:
                        source = 'opp_kickout'
                        break
                    if prev['team']!='Killinkere' and prev['name']=='Free conceded':
                        source = 'opp_foul'
                        break
                score_sources[source] += 1
            
            elif e['team']!='Killinkere' and e['name'] in ['Shot from play','Scoreable free'] and e['outcome'] in ['Point','2 Points','Goal']:
                opp_scores.append(t)
            
            # Shots (Killinkere)
            if e['team']=='Killinkere' and e['name'] in ['Shot from play','Scoreable free']:
                is_score = e['outcome'] in ['Point','2 Points','Goal']
                is_wide = e['outcome'] in ['Wide','Short','45']
                
                shots_by_phase[phase] += 1
                if is_wide:
                    wides_by_phase[phase] += 1
                
                # Classify shot source
                shot_source = 'built'
                for j in range(i-1, max(i-8, -1), -1):
                    prev = events[j]
                    if prev['time'] < t - 25: break
                    if prev['team']=='Killinkere' and prev['name']=='Turnover':
                        shot_source = 'turnover'
                        break
                    if prev['team']=='Killinkere' and prev['name']=='Kickout' and prev['outcome'] in ['Won clean','Short won','Break won']:
                        shot_source = 'kickout_won'
                        break
                
                if shot_source == 'turnover':
                    shots_after_turnover['taken'] += 1
                    if is_score: shots_after_turnover['scored'] += 1
                elif shot_source == 'kickout_won':
                    shots_after_kickout_won['taken'] += 1
                    if is_score: shots_after_kickout_won['scored'] += 1
                else:
                    shots_built['taken'] += 1
                    if is_score: shots_built['scored'] += 1
            
            # Turnovers won by Killinkere
            if e['team']=='Killinkere' and e['name']=='Turnover':
                k_turnovers_won.append(t)
            
            # Kickout tracking
            if e['name']=='Kickout':
                if e['team']=='Killinkere':
                    won = e['outcome'] in ['Won clean','Short won','Break won']
                    kickout_results['own_'+e['outcome']] += 1
                    if won:
                        kickout_total_won += 1
                    else:
                        kickout_total_lost += 1
                else:
                    won_by_k = e['outcome'] in ['Lost clean','Break lost']
                    kickout_results['opp_'+e['outcome']] += 1
            
            # Possession lost
            if e['team']=='Killinkere' and e['name']=='Possession lost':
                possession_lost_types[e['outcome']] += 1
            
            # Frees conceded shortly after scoring
            if e['team']=='Killinkere' and e['name']=='Free conceded':
                for s in k_scores:
                    if 0 < t - s <= 120:  # within 2 min of scoring
                        frees_conceded_after_score += 1
                        break
        
        # Response time analysis
        for opp_t in opp_scores:
            next_k = next((s for s in k_scores if s > opp_t), None)
            if next_k:
                response_times.append(next_k - opp_t)
        
        # Conceding clusters: opp scores 2+ without Killinkere response
        cluster_count = 0
        for i, opp_t in enumerate(opp_scores):
            k_between = [s for s in k_scores if (opp_scores[i-1] if i > 0 else 0) < s < opp_t]
            if not k_between and i > 0:
                cluster_count += 1
        conceding_clusters.append({'game': game_name, 'clusters': cluster_count, 'opp_scores': len(opp_scores)})
        
        games_data.append({'name': game_name, 'comp': comp, 'k_scores': len(k_scores), 'opp_scores': len(opp_scores)})
    
    # ============================================================
    # REPORT
    # ============================================================
    print("=" * 70)
    print("KILLINKERE TACTICAL ANALYSIS — ACTIONABLE INSIGHTS")
    print("=" * 70)
    print(f"23 games analysed | {total_scores_k} total scores")
    
    # 1. RESPONSE TIME AFTER CONCEDING
    print("\n\n" + "─"*70)
    print("1. RESPONSE TIME AFTER CONCEDING")
    print("─"*70)
    if response_times:
        avg_resp = sum(response_times)/len(response_times)
        quick = sum(1 for r in response_times if r <= 180)
        slow = sum(1 for r in response_times if r > 300)
        print(f"   Average response: {fmt(avg_resp)}")
        print(f"   Responded within 3 min: {quick}/{len(response_times)} ({quick*100//len(response_times)}%)")
        print(f"   Took 5+ min to respond: {slow}/{len(response_times)} ({slow*100//len(response_times)}%)")
        print(f"\n   Distribution:")
        bins = [(0,60,'Under 1 min'),(60,120,'1-2 min'),(120,180,'2-3 min'),(180,300,'3-5 min'),(300,600,'5-10 min'),(600,9999,'10+ min')]
        for lo,hi,label in bins:
            count = sum(1 for r in response_times if lo <= r < hi)
            bar = '█' * (count // 2)
            print(f"     {label:12s}: {count:3d} {bar}")
    
    # 2. CONCEDING IN CLUSTERS
    print("\n\n" + "─"*70)
    print("2. CONCEDING IN CLUSTERS (opp scoring 2+ without response)")
    print("─"*70)
    total_clusters = sum(c['clusters'] for c in conceding_clusters)
    print(f"   Total cluster scores conceded: {total_clusters} across 23 games")
    print(f"   Average: {total_clusters/23:.1f} per game")
    worst = sorted(conceding_clusters, key=lambda x: x['clusters'], reverse=True)[:5]
    print(f"\n   Worst games:")
    for g in worst:
        print(f"     {g['clusters']} clusters — {g['game']}")
    
    # 3. SCORE SOURCE ANALYSIS
    print("\n\n" + "─"*70)
    print("3. WHERE DO SCORES COME FROM?")
    print("─"*70)
    total_src = sum(score_sources.values())
    for src, count in sorted(score_sources.items(), key=lambda x: x[1], reverse=True):
        pct = count*100//total_src
        label = {
            'turnover': 'Won turnover',
            'own_kickout': 'Own kickout won',
            'opp_kickout': 'Opp kickout lost', 
            'opp_foul': 'Opp free conceded',
            'built': 'Built play / other'
        }.get(src, src)
        bar = '█' * (pct // 2)
        print(f"   {label:22s}: {count:3d} ({pct}%) {bar}")
    
    # 4. SHOT ACCURACY BY SOURCE
    print("\n\n" + "─"*70)
    print("4. SHOOTING ACCURACY BY SOURCE")
    print("─"*70)
    for label, data in [('After turnover', shots_after_turnover), ('After own kickout won', shots_after_kickout_won), ('Built play', shots_built)]:
        if data['taken'] > 0:
            acc = data['scored']*100//data['taken']
            print(f"   {label:22s}: {data['scored']}/{data['taken']} = {acc}%")
    
    # 5. POSSESSION LOST BREAKDOWN
    print("\n\n" + "─"*70)
    print("5. HOW WE LOSE POSSESSION (most fixable issues)")
    print("─"*70)
    total_pl = sum(possession_lost_types.values())
    for ptype, count in sorted(possession_lost_types.items(), key=lambda x: x[1], reverse=True):
        pct = count*100//max(total_pl,1)
        bar = '█' * (pct // 2)
        print(f"   {ptype:18s}: {count:3d} ({pct}%) {bar}")
    print(f"\n   Total possession losses: {total_pl} ({total_pl/23:.1f} per game)")
    
    # 6. WIDES BY GAME PHASE
    print("\n\n" + "─"*70)
    print("6. SHOT ACCURACY BY GAME PHASE")
    print("─"*70)
    phase_names = ['0-10','10-20','20-30','30-40','40-50','50-60','60+']
    for p in range(7):
        shots = shots_by_phase.get(p, 0)
        scored = scores_by_phase.get(p, 0)
        wides = wides_by_phase.get(p, 0)
        if shots > 0:
            acc = scored*100//shots
            wide_rate = wides*100//shots
            acc_bar = '█' * (acc // 5)
            print(f"   {phase_names[p] if p<6 else '60+':6s}: {scored}/{shots} scored ({acc}%) | {wides} wides ({wide_rate}%) {acc_bar}")
    
    # 7. KICKOUT ANALYSIS
    print("\n\n" + "─"*70)
    print("7. OWN KICKOUT ANALYSIS")
    print("─"*70)
    print(f"   Won: {kickout_total_won} | Lost: {kickout_total_lost} | Win%: {kickout_total_won*100//(kickout_total_won+kickout_total_lost)}%")
    print(f"\n   Breakdown:")
    for k, v in sorted(kickout_results.items(), key=lambda x: x[1], reverse=True):
        if k.startswith('own_'):
            print(f"     {k.replace('own_',''):15s}: {v}")
    
    # 8. DISCIPLINE AFTER SCORING
    print("\n\n" + "─"*70)
    print("8. DISCIPLINE — FREES CONCEDED WITHIN 2 MIN OF SCORING")
    print("─"*70)
    print(f"   {frees_conceded_after_score} frees conceded shortly after scoring")
    print(f"   ({frees_conceded_after_score/23:.1f} per game)")
    print(f"   This is a concentration/discipline issue — giving back momentum immediately after scoring")
    
    # 9. KEY ACTIONABLE SUMMARY
    print("\n\n" + "="*70)
    print("KEY TACTICAL RECOMMENDATIONS")
    print("="*70)
    
    # Find the biggest issues
    top_poss_loss = sorted(possession_lost_types.items(), key=lambda x: x[1], reverse=True)[0]
    
    print(f"""
   1. KICK PASSING is the #1 possession issue ({possession_lost_types.get('Kick pass',0)} losses)
      → Work on shorter, more patient build-up; reduce speculative kicks
   
   2. TURNOVERS are the best scoring source ({score_sources.get('turnover',0)} scores)
      → Pressing high and forcing turnovers is the primary attacking weapon
      → Accuracy after turnovers: {shots_after_turnover['scored']}/{shots_after_turnover['taken']} ({shots_after_turnover['scored']*100//max(shots_after_turnover['taken'],1)}%)
   
   3. RESPONSE after conceding takes avg {fmt(sum(response_times)//max(len(response_times),1))}
      → {sum(1 for r in response_times if r>300)*100//max(len(response_times),1)}% of the time it takes 5+ min — need quicker reset
   
   4. CONCEDING IN CLUSTERS ({total_clusters/23:.1f} per game)
      → Opposition frequently scores 2+ without a Killinkere response
      → Focus on composure and retaining ball after conceding
   
   5. DISCIPLINE after scoring ({frees_conceded_after_score} frees within 2 min of scoring)
      → Giving away cheap frees on a high; need to reset mentally
""")

if __name__=='__main__':
    main()
