#!/usr/bin/env python3
"""Generate HTML tactical analysis infographic with competition filters."""

import csv, os, glob, json, difflib
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
    if 'div 3' in c: return 'ACFL Div 3'
    elif 'div 7' in c or 'div 5' in c: return 'ACFL Div 7'
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
            })
    except: pass
    return events

def analyze_games(game_list):
    """Analyze a list of (game_name, events) and return stats dict."""
    response_times = []
    cluster_total = 0
    score_sources = defaultdict(int)
    shots_by_source = {'turnover':{'t':0,'s':0},'kickout':{'t':0,'s':0},'built':{'t':0,'s':0}}
    poss_lost = defaultdict(int)
    wides_phase = defaultdict(int)
    scores_phase = defaultdict(int)
    shots_phase = defaultdict(int)
    frees_after_score = 0
    total_scores = 0
    ko_won = 0
    ko_lost = 0
    n = len(game_list)

    for game_name, events in game_list:
        k_scores = []
        opp_scores = []

        for i, e in enumerate(events):
            t = e['time']
            phase = min(t // 600, 6)

            if e['team']=='Killinkere' and e['name'] in ['Shot from play','Scoreable free'] and e['outcome'] in ['Point','2 Points','Goal']:
                k_scores.append(t)
                total_scores += 1
                scores_phase[phase] += 1
                # Source
                source = 'built'
                for j in range(i-1, max(i-8,-1), -1):
                    p = events[j]
                    if p['time'] < t - 30: break
                    if p['team']=='Killinkere' and p['name']=='Turnover':
                        source = 'turnover'; break
                    if p['team']=='Killinkere' and p['name']=='Kickout' and p['outcome'] in ['Won clean','Short won','Break won']:
                        source = 'own_kickout'; break
                    if p['team']!='Killinkere' and p['name']=='Kickout' and p['outcome'] in ['Lost clean','Break lost']:
                        source = 'opp_kickout'; break
                    if p['team']!='Killinkere' and p['name']=='Free conceded':
                        source = 'opp_foul'; break
                score_sources[source] += 1

            elif e['team']!='Killinkere' and e['name'] in ['Shot from play','Scoreable free'] and e['outcome'] in ['Point','2 Points','Goal']:
                opp_scores.append(t)

            # Shots
            if e['team']=='Killinkere' and e['name'] in ['Shot from play','Scoreable free']:
                is_score = e['outcome'] in ['Point','2 Points','Goal']
                is_wide = e['outcome'] in ['Wide','Short','45']
                shots_phase[phase] += 1
                if is_wide: wides_phase[phase] += 1
                # Source
                ss = 'built'
                for j in range(i-1, max(i-8,-1), -1):
                    p = events[j]
                    if p['time'] < t - 25: break
                    if p['team']=='Killinkere' and p['name']=='Turnover':
                        ss = 'turnover'; break
                    if p['team']=='Killinkere' and p['name']=='Kickout' and p['outcome'] in ['Won clean','Short won','Break won']:
                        ss = 'kickout'; break
                shots_by_source[ss]['t'] += 1
                if is_score: shots_by_source[ss]['s'] += 1

            if e['team']=='Killinkere' and e['name']=='Possession lost':
                poss_lost[e['outcome']] += 1

            if e['name']=='Kickout' and e['team']=='Killinkere':
                if e['outcome'] in ['Won clean','Short won','Break won']: ko_won += 1
                elif e['outcome'] in ['Lost clean','Break lost','Sideline ball','Short lost']: ko_lost += 1

            if e['team']=='Killinkere' and e['name']=='Free conceded':
                for s in k_scores:
                    if 0 < t - s <= 120:
                        frees_after_score += 1
                        break

        # Response times
        for ot in opp_scores:
            nk = next((s for s in k_scores if s > ot), None)
            if nk: response_times.append(nk - ot)

        # Clusters
        for i, ot in enumerate(opp_scores):
            if i > 0:
                k_between = [s for s in k_scores if opp_scores[i-1] < s < ot]
                if not k_between: cluster_total += 1

    # Build result
    avg_resp = sum(response_times)//max(len(response_times),1) if response_times else 0
    resp_quick = sum(1 for r in response_times if r <= 180)
    resp_slow = sum(1 for r in response_times if r > 300)
    resp_total = len(response_times)

    # Response distribution
    resp_dist = []
    for lo,hi in [(0,60),(60,120),(120,180),(180,300),(300,600),(600,9999)]:
        resp_dist.append(sum(1 for r in response_times if lo <= r < hi))

    # Phase accuracy
    phase_acc = []
    for p in range(7):
        sh = shots_phase.get(p,0)
        sc = scores_phase.get(p,0)
        w = wides_phase.get(p,0)
        phase_acc.append({'shots':sh,'scores':sc,'wides':w,'acc':round(sc*100/max(sh,1)),'wide_rate':round(w*100/max(sh,1))})

    # Poss lost sorted
    pl_total = sum(poss_lost.values())
    pl_sorted = sorted(poss_lost.items(), key=lambda x:x[1], reverse=True)[:6]

    return {
        'n': n,
        'total_scores': total_scores,
        'avg_response': fmt(avg_resp),
        'resp_quick_pct': round(resp_quick*100/max(resp_total,1)),
        'resp_slow_pct': round(resp_slow*100/max(resp_total,1)),
        'resp_dist': resp_dist,
        'clusters_pg': round(cluster_total/max(n,1), 1),
        'score_sources': {
            'built': score_sources.get('built',0),
            'turnover': score_sources.get('turnover',0),
            'own_kickout': score_sources.get('own_kickout',0),
            'opp_kickout': score_sources.get('opp_kickout',0),
            'opp_foul': score_sources.get('opp_foul',0),
        },
        'shots_by_source': {
            'turnover_s': shots_by_source['turnover']['s'],
            'turnover_t': shots_by_source['turnover']['t'],
            'kickout_s': shots_by_source['kickout']['s'],
            'kickout_t': shots_by_source['kickout']['t'],
            'built_s': shots_by_source['built']['s'],
            'built_t': shots_by_source['built']['t'],
        },
        'poss_lost': [{'type':t,'count':c,'pct':round(c*100/max(pl_total,1))} for t,c in pl_sorted],
        'poss_lost_total': pl_total,
        'poss_lost_pg': round(pl_total/max(n,1), 1),
        'phase_acc': phase_acc,
        'ko_won': ko_won,
        'ko_lost': ko_lost,
        'ko_pct': round(ko_won*100/max(ko_won+ko_lost,1)),
        'frees_after_score': frees_after_score,
        'frees_after_score_pg': round(frees_after_score/max(n,1), 1),
    }

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir,'Killinkere*.csv')))

    # Load all games
    all_games = []
    for fp in csv_files:
        name = os.path.basename(fp).replace('.csv','').replace('Killinkere ','')
        meta = load_meta(fp)
        comp = classify(meta.get('competition',''))
        events = load_game(fp)
        if events:
            all_games.append((name, comp, events))

    # Compute per filter
    filters = ['All','ACFL Div 3','ACFL Div 7','Spring League','Challenge']
    filter_data = {}
    for f in filters:
        subset = [(name,ev) for name,comp,ev in all_games] if f=='All' else [(name,ev) for name,comp,ev in all_games if comp==f]
        filter_data[f] = analyze_games(subset)

    fd_json = json.dumps(filter_data)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Killinkere Tactical Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}}
.ctr{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.hdr{{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:30px;text-align:center;border-radius:20px 20px 0 0}}
.hdr h1{{font-size:2.2em;margin-bottom:6px}}
.hdr .sub{{opacity:.8;margin-top:8px}}
.flt{{display:flex;justify-content:center;gap:8px;padding:16px;background:#34495e;flex-wrap:wrap}}
.fb{{padding:9px 18px;border-radius:20px;border:2px solid #fff;background:transparent;color:#fff;font-weight:bold;font-size:.85em;cursor:pointer;transition:.3s}}
.fb:hover{{background:rgba(255,255,255,.15)}}.fb.active{{background:#2a5298;border-color:#4ecdc4;color:#4ecdc4}}
.cnt{{padding:25px 35px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0}}
.cd{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:12px;padding:16px;text-align:center}}
.cd .v{{font-size:1.8em;font-weight:bold}}.cd .l{{font-size:.75em;opacity:.85;margin-top:3px}}
.pnl{{background:#fff;border-radius:14px;padding:22px;margin:20px 0;box-shadow:0 3px 6px rgba(0,0,0,.08);border:1px solid #ecf0f1}}
.pnl h3{{font-size:1.2em;color:#2c3e50;margin-bottom:10px;text-align:center}}
.pnl .sub{{font-size:.82em;color:#7f8c8d;text-align:center;margin-bottom:10px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:900px){{.g2{{grid-template-columns:1fr}}}}
.bar-row{{display:flex;align-items:center;margin:8px 0;gap:10px}}
.bar-label{{min-width:110px;font-size:.85em;color:#2c3e50;font-weight:600}}
.bar-track{{flex:1;height:26px;background:#ecf0f1;border-radius:13px;overflow:hidden;position:relative}}
.bar-fill{{height:100%;border-radius:13px;display:flex;align-items:center;padding:0 10px;color:#fff;font-size:.8em;font-weight:bold;transition:width .5s}}
.bar-val{{min-width:50px;font-size:.85em;color:#555;text-align:right}}
.ins{{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;border-radius:12px;padding:22px;margin:20px 0}}
.ins h3{{margin-bottom:14px;font-size:1.2em}}
.ins-i{{display:flex;gap:10px;margin:10px 0;padding:10px;background:rgba(255,255,255,.08);border-radius:8px;font-size:.9em;line-height:1.4}}
.phase-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center;margin:10px 0}}
.phase-cell{{padding:10px 4px;border-radius:8px;font-size:.75em}}
.phase-cell .pv{{font-size:1.4em;font-weight:bold;margin-bottom:2px}}
</style>
</head>
<body>
<div class="ctr">
<div class="hdr">
<h1>TACTICAL ANALYSIS</h1>
<div style="font-size:1.1em">Killinkere \u2014 2026 Season</div>
<div class="sub" id="hdr-sub"></div>
</div>
<div class="flt">
<button class="fb active" onclick="pick('All')">All (23)</button>
<button class="fb" onclick="pick('ACFL Div 3')">Div 3 (8)</button>
<button class="fb" onclick="pick('ACFL Div 7')">Div 7 (7)</button>
<button class="fb" onclick="pick('Spring League')">Spring League (5)</button>
<button class="fb" onclick="pick('Challenge')">Challenge (3)</button>
</div>
<div class="cnt">
<div class="cards" id="cards"></div>

<div class="g2">
<div class="pnl"><h3>Where Do Scores Come From?</h3><div class="sub">Source of possession before each score</div><canvas id="c1" height="130"></canvas></div>
<div class="pnl"><h3>Shot Accuracy by Source</h3><div class="sub">Conversion rate depending on how possession was won</div><canvas id="c2" height="130"></canvas></div>
</div>

<div class="pnl"><h3>Response Time After Conceding</h3><div class="sub">How quickly Killinkere score after the opposition scores</div>
<div class="g2">
<canvas id="c3" height="120"></canvas>
<div id="resp-info" style="display:flex;flex-direction:column;justify-content:center;padding:10px;"></div>
</div></div>

<div class="pnl"><h3>How Possession is Lost</h3><div class="sub">The fixable errors — where the ball is being given away</div><div id="poss-bars"></div></div>

<div class="pnl"><h3>Shot Accuracy by Game Phase</h3><div class="sub">Accuracy % and wide rate across 10-minute windows</div><div id="phase-grid"></div></div>

<div class="g2">
<div class="pnl"><h3>Own Kickout Win Rate</h3><canvas id="c4" height="120"></canvas></div>
<div class="pnl"><h3>Conceding in Clusters</h3><div class="sub">Opposition scoring 2+ unanswered</div><div id="cluster-info" style="text-align:center;padding:20px;"></div></div>
</div>

<div class="ins" id="insights"></div>
</div>
</div>
<script>
const D={fd_json};
let C={{}};
function pick(f){{
document.querySelectorAll('.fb').forEach(b=>b.classList.toggle('active',b.textContent.includes(f==='All'?'All':f)));
render(f);
}}
function render(f){{
const d=D[f];
document.getElementById('hdr-sub').textContent=d.n+' games | '+d.total_scores+' scores analysed';

document.getElementById('cards').innerHTML=`
<div class="cd"><div class="v">${{d.avg_response}}</div><div class="l">Avg Response Time</div></div>
<div class="cd"><div class="v">${{d.clusters_pg}}</div><div class="l">Clusters Conceded/Game</div></div>
<div class="cd"><div class="v">${{d.poss_lost_pg}}</div><div class="l">Poss. Lost/Game</div></div>
<div class="cd"><div class="v">${{d.ko_pct}}%</div><div class="l">Own Kickout Win%</div></div>
<div class="cd"><div class="v">${{d.frees_after_score_pg}}</div><div class="l">Frees After Scoring/Game</div></div>`;

Object.values(C).forEach(c=>c.destroy());C={{}};

// Score sources
const ss=d.score_sources;
C.c1=new Chart(document.getElementById('c1'),{{type:'doughnut',data:{{
labels:['Built Play','Turnover','Own Kickout','Opp Kickout','Opp Foul'],
datasets:[{{data:[ss.built,ss.turnover,ss.own_kickout,ss.opp_kickout,ss.opp_foul],
backgroundColor:['rgba(52,152,219,.8)','rgba(46,204,113,.8)','rgba(155,89,182,.8)','rgba(243,156,18,.8)','rgba(231,76,60,.8)'],borderWidth:2,borderColor:'#fff'}}]
}},options:{{responsive:true,animation:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:11}}}}}}}}}}}});

// Accuracy by source
const sb=d.shots_by_source;
const accT=sb.turnover_t?Math.round(sb.turnover_s*100/sb.turnover_t):0;
const accK=sb.kickout_t?Math.round(sb.kickout_s*100/sb.kickout_t):0;
const accB=sb.built_t?Math.round(sb.built_s*100/sb.built_t):0;
C.c2=new Chart(document.getElementById('c2'),{{type:'bar',data:{{
labels:['After Turnover','After Kickout Won','Built Play'],
datasets:[{{data:[accT,accK,accB],backgroundColor:['rgba(46,204,113,.8)','rgba(155,89,182,.8)','rgba(52,152,219,.8)'],borderWidth:0}}]
}},options:{{responsive:true,animation:false,indexAxis:'y',scales:{{x:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}},plugins:{{legend:{{display:false}}}}}}}});

// Response time
const rd=d.resp_dist;
C.c3=new Chart(document.getElementById('c3'),{{type:'bar',data:{{
labels:['<1m','1-2m','2-3m','3-5m','5-10m','10+m'],
datasets:[{{data:rd,backgroundColor:['rgba(46,204,113,.8)','rgba(46,204,113,.6)','rgba(243,156,18,.6)','rgba(243,156,18,.8)','rgba(231,76,60,.7)','rgba(231,76,60,.9)'],borderWidth:0}}]
}},options:{{responsive:true,animation:false,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});

document.getElementById('resp-info').innerHTML=`
<div style="text-align:center">
<div style="font-size:2.5em;font-weight:bold;color:#2c3e50">${{d.avg_response}}</div>
<div style="color:#7f8c8d;margin:5px 0">Average Response</div>
<div style="margin-top:15px;display:flex;gap:15px;justify-content:center">
<div style="text-align:center"><div style="font-size:1.5em;font-weight:bold;color:#27ae60">${{d.resp_quick_pct}}%</div><div style="font-size:.75em;color:#555">Within 3 min</div></div>
<div style="text-align:center"><div style="font-size:1.5em;font-weight:bold;color:#e74c3c">${{d.resp_slow_pct}}%</div><div style="font-size:.75em;color:#555">5+ min</div></div>
</div></div>`;

// Possession lost bars
let pb='';
d.poss_lost.forEach(p=>{{
const col=p.pct>=30?'rgba(231,76,60,.85)':p.pct>=20?'rgba(243,156,18,.8)':'rgba(52,152,219,.7)';
pb+=`<div class="bar-row"><div class="bar-label">${{p.type}}</div><div class="bar-track"><div class="bar-fill" style="width:${{p.pct}}%;background:${{col}}">${{p.count}}</div></div><div class="bar-val">${{p.pct}}%</div></div>`;
}});
pb+=`<div style="text-align:center;margin-top:10px;font-size:.85em;color:#7f8c8d">${{d.poss_lost_total}} total (${{d.poss_lost_pg}}/game)</div>`;
document.getElementById('poss-bars').innerHTML=pb;

// Phase accuracy grid
const phases=['0-10','10-20','20-30','30-40','40-50','50-60','60+'];
let pg='<div class="phase-grid">';
d.phase_acc.forEach((p,i)=>{{
const col=p.acc>=60?'#d4edda':p.acc>=50?'#fff3cd':'#ffe0e0';
const tc=p.acc>=60?'#155724':p.acc>=50?'#856404':'#c0392b';
pg+=`<div class="phase-cell" style="background:${{col}}"><div class="pv" style="color:${{tc}}">${{p.acc}}%</div><div style="color:${{tc}}">${{phases[i]}}</div><div style="font-size:.7em;color:#555;margin-top:3px">${{p.scores}}/${{p.shots}} shots</div><div style="font-size:.7em;color:#c0392b">${{p.wides}} wides (${{p.wide_rate}}%)</div></div>`;
}});
pg+='</div>';
document.getElementById('phase-grid').innerHTML=pg;

// Kickout donut
C.c4=new Chart(document.getElementById('c4'),{{type:'doughnut',data:{{
labels:['Won','Lost'],
datasets:[{{data:[d.ko_won,d.ko_lost],backgroundColor:['rgba(46,204,113,.8)','rgba(231,76,60,.7)'],borderWidth:2,borderColor:'#fff'}}]
}},options:{{responsive:true,animation:false,plugins:{{legend:{{position:'bottom'}}}}}}}});

// Clusters
document.getElementById('cluster-info').innerHTML=`
<div style="font-size:3em;font-weight:bold;color:#e74c3c">${{d.clusters_pg}}</div>
<div style="color:#555;margin:8px 0">unanswered runs per game</div>
<div style="font-size:.85em;color:#7f8c8d;margin-top:10px">Opposition scoring 2+ times without<br>a Killinkere score in between</div>`;

// Insights
const topPL=d.poss_lost[0];
const bestSrc=Object.entries(d.score_sources).sort((a,b)=>b[1]-a[1]);
const turnAcc=sb.turnover_t?Math.round(sb.turnover_s*100/sb.turnover_t):0;
const builtAcc=sb.built_t?Math.round(sb.built_s*100/sb.built_t):0;
const accDiff=turnAcc-builtAcc;
var turnInsight='';
if(accDiff>0){{turnInsight='<strong>Turnovers</strong> produce '+accDiff+'% better accuracy ('+turnAcc+'% vs '+builtAcc+'% from built play). High press is the best attacking strategy.';}}
else{{turnInsight='<strong>Built play</strong> is more accurate ('+builtAcc+'%) than after turnovers ('+turnAcc+'%). Patience in possession pays off - work the ball rather than rushing shots on the counter.';}}

var insHtml='<h3>Key Recommendations - '+f+'</h3>';
insHtml+='<div class="ins-i"><span>\u26a0\ufe0f</span><span><strong>'+topPL.type+'</strong> is the #1 possession problem ('+topPL.count+' losses, '+topPL.pct+'%). Reduce speculative ball and work shorter options.</span></div>';
insHtml+='<div class="ins-i"><span>\u2705</span><span>'+turnInsight+'</span></div>';
insHtml+='<div class="ins-i"><span>\u23f1\ufe0f</span><span><strong>Response time:</strong> '+d.resp_slow_pct+'% of the time it takes 5+ min to respond after conceding. Need faster reset - composure on kickout.</span></div>';
insHtml+='<div class="ins-i"><span>\u26a0\ufe0f</span><span><strong>Clusters:</strong> '+d.clusters_pg+' times/game the opposition scores 2+ unanswered. Ball retention after conceding needs focus.</span></div>';
insHtml+='<div class="ins-i"><span>\u26a0\ufe0f</span><span><strong>Discipline:</strong> '+d.frees_after_score_pg+' frees/game conceded within 2 min of scoring. Mental reset needed after putting up a score.</span></div>';
document.getElementById('insights').innerHTML=insHtml;
}}
render('All');
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body></html>'''

    out = os.path.join(data_dir, 'Killinkere_tactical_analysis.html')
    with open(out, 'w') as f:
        f.write(html)
    print(f"Saved: {out}")

if __name__ == '__main__':
    main()
