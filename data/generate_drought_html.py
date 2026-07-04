#!/usr/bin/env python3
"""Generate a lightweight HTML drought infographic — no dynamic chart re-rendering."""

import csv, os, glob, json
import numpy as np

def parse_time(time_str):
    parts = time_str.strip().split(':')
    if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    elif len(parts) == 2: return int(parts[0])*60 + int(parts[1])
    return 0

def is_killinkere_score(row):
    return (row.get('Team Name','') == 'Killinkere' and
            row.get('Name','') in ['Shot from play','Scoreable free'] and
            row.get('Outcome','') in ['Point','2 Points','Goal'])

def analyze_game(filepath):
    droughts, scores = [], []
    try:
        for enc in ['utf-8','utf-8-sig','latin-1','cp1252']:
            try:
                with open(filepath,'r',encoding=enc) as f: content = f.read()
                break
            except UnicodeDecodeError: continue
        lines = content.replace('\r\n','\n').replace('\r','\n').split('\n')
        clean = []
        for l in lines:
            if l.strip()=='' or l.startswith('='): break
            clean.append(l)
        if not clean: return [],[]
        reader = csv.DictReader(clean)
        game_end = 0
        for row in reader:
            t_str = row.get('Time','')
            if not t_str: continue
            t = parse_time(t_str)
            game_end = max(game_end, t)
            if is_killinkere_score(row): scores.append(t)
        if not scores:
            if game_end > 0: droughts.append({'s':0,'e':game_end,'d':game_end})
            return droughts, scores
        if scores[0] > 0: droughts.append({'s':0,'e':scores[0],'d':scores[0]})
        for i in range(len(scores)-1):
            droughts.append({'s':scores[i],'e':scores[i+1],'d':scores[i+1]-scores[i]})
        if scores[-1] < game_end:
            droughts.append({'s':scores[-1],'e':game_end,'d':game_end-scores[-1]})
    except: pass
    return droughts, scores

def load_meta(filepath):
    import difflib
    meta = {}
    meta_path = filepath.replace('.csv','.meta')
    if os.path.exists(meta_path):
        with open(meta_path,'r') as f:
            for line in f:
                if '=' in line:
                    k,v = line.strip().split('=',1)
                    meta[k.strip()] = v.strip()
    if not meta:
        data_dir = os.path.dirname(filepath)
        base = os.path.basename(filepath).replace('.csv','')
        all_metas = glob.glob(os.path.join(data_dir,'Killinkere*.meta'))
        meta_bases = [os.path.basename(m).replace('.meta','') for m in all_metas]
        matches = difflib.get_close_matches(base, meta_bases, n=1, cutoff=0.85)
        if matches:
            with open(os.path.join(data_dir, matches[0]+'.meta'),'r') as f:
                for line in f:
                    if '=' in line:
                        k,v = line.strip().split('=',1)
                        meta[k.strip()] = v.strip()
    return meta

def classify(comp_str):
    comp = comp_str.lower()
    if 'div 3' in comp: return 'ACFL Div 3'
    elif 'div 7' in comp or 'div 5' in comp: return 'ACFL Div 7'
    elif 'spring league' in comp: return 'Spring League'
    elif 'challenge' in comp: return 'Challenge'
    return 'Other'

def fmt(sec):
    m,s = divmod(int(sec),60)
    return f"{m:02d}:{s:02d}"

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir,'Killinkere*.csv')))

    games = []
    for fp in csv_files:
        name = os.path.basename(fp).replace('.csv','')
        meta = load_meta(fp)
        comp = classify(meta.get('competition','Unknown'))
        droughts, scores = analyze_game(fp)
        games.append({'name':name,'comp':comp,'droughts':droughts,'scores':scores})

    all_comps = ['All','ACFL Div 3','ACFL Div 7','Spring League','Challenge']
    
    # Pre-compute all data per filter
    filter_data = {}
    for comp_filter in all_comps:
        fg = games if comp_filter == 'All' else [g for g in games if g['comp'] == comp_filter]
        n = len(fg)
        all_d = [d for g in fg for d in g['droughts']]
        sig = [d for d in all_d if d['d'] >= 300]
        
        # Scoring by minute
        bins = [0]*65
        for g in fg:
            for s in g['scores']:
                m = int(s/60)
                if m < 65: bins[m] += 1
        normed = [b/max(n,1) for b in bins]
        # Smooth
        smoothed = []
        for i in range(65):
            s_i = max(0,i-1); e_i = min(64,i+1)
            smoothed.append(sum(normed[s_i:e_i+1])/(e_i-s_i+1))
        
        # Phase data
        ranges = [(0,600),(600,1200),(1200,1800),(1800,2400),(2400,3000),(3000,3600)]
        phase_counts = [sum(1 for d in sig if s<=d['s']<e) for s,e in ranges]
        phase_per_game = [c/max(n,1) for c in phase_counts]
        phase_avg_dur = []
        for s,e in ranges:
            pd = [d['d'] for d in all_d if s<=d['s']<e and d['d']>0]
            phase_avg_dur.append(sum(pd)/len(pd)/60 if pd else 0)
        
        # Stats
        longest = max((d['d'] for d in sig), default=0)
        avg_sig = sum(d['d'] for d in sig)/len(sig) if sig else 0
        openings = [d['d'] for d in all_d if d['s']==0]
        avg_open = sum(openings)/len(openings) if openings else 0
        dpg = len(sig)/max(n,1)
        
        # Half comparison
        h1 = [d for d in sig if d['s']<1800]
        h2 = [d for d in sig if d['s']>=1800]
        
        # Top droughts
        top10 = sorted(sig, key=lambda d:d['d'], reverse=True)[:10]
        top10_info = []
        for d in top10:
            game = next((g for g in fg if any(gd['s']==d['s'] and gd['e']==d['e'] for gd in g['droughts'])), None)
            top10_info.append({
                'dur': fmt(d['d']),
                'window': f"{fmt(d['s'])} → {fmt(d['e'])}",
                'half': '1st' if d['s']<1800 else '2nd',
                'game': game['name'].replace('Killinkere ','') if game else '?',
                'comp': game['comp'] if game else ''
            })
        
        # Heatmap data
        heatmap = []
        for g in fg:
            gd = [d for d in g['droughts'] if d['d']>=300]
            heatmap.append({'name': g['name'].replace('Killinkere ','')[:30], 'droughts': gd})
        
        filter_data[comp_filter] = {
            'n': n, 'dpg': round(dpg,1), 'avg_sig': fmt(avg_sig), 'longest': fmt(longest),
            'avg_open': fmt(avg_open), 'smoothed': [round(v,3) for v in smoothed],
            'phase_per_game': [round(v,2) for v in phase_per_game],
            'phase_avg_dur': [round(v,1) for v in phase_avg_dur],
            'h1_count': len(h1), 'h2_count': len(h2),
            'h1_avg': round(sum(d['d'] for d in h1)/max(len(h1),1)/60, 1),
            'h2_avg': round(sum(d['d'] for d in h2)/max(len(h2),1)/60, 1),
            'h1_pg': round(len(h1)/max(n,1), 1), 'h2_pg': round(len(h2)/max(n,1), 1),
            'top10': top10_info, 'heatmap': heatmap,
            'open_slow': sum(1 for o in openings if o>=300),
            'open_total': len(openings)
        }

    fd_json = json.dumps(filter_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Killinkere Scoring Drought Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:35px;text-align:center;border-radius:20px 20px 0 0}}
.header h1{{font-size:2.3em;margin-bottom:8px}}
.header .sub{{font-size:1em;opacity:.8;margin-top:10px}}
.filters{{display:flex;justify-content:center;gap:8px;padding:18px;background:#34495e;flex-wrap:wrap}}
.fbtn{{padding:9px 18px;border-radius:20px;border:2px solid #fff;background:transparent;color:#fff;font-weight:bold;font-size:.85em;cursor:pointer;transition:.3s}}
.fbtn:hover{{background:rgba(255,255,255,.15)}}
.fbtn.active{{background:#2a5298;border-color:#4ecdc4;color:#4ecdc4}}
.content{{padding:25px 35px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}}
.card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:12px;padding:18px;text-align:center}}
.card .v{{font-size:2em;font-weight:bold}}.card .l{{font-size:.8em;opacity:.85;margin-top:4px}}
.panel{{background:#fff;border-radius:14px;padding:22px;margin:20px 0;box-shadow:0 3px 6px rgba(0,0,0,.08);border:1px solid #ecf0f1}}
.panel h3{{font-size:1.3em;color:#2c3e50;margin-bottom:12px;text-align:center}}
.panel .sub{{font-size:.85em;color:#7f8c8d;text-align:center;margin-bottom:12px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:900px){{.g2{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th{{background:#34495e;color:#fff;padding:10px 12px;text-align:left;font-size:.9em}}
td{{padding:8px 12px;border-bottom:1px solid #ecf0f1;font-size:.85em}}
tr:hover{{background:#f8f9fa}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.7em;font-weight:bold}}
.bd{{background:#ffe0e0;color:#c0392b}}.bw{{background:#fff3cd;color:#856404}}.bs{{background:#d4edda;color:#155724}}
.hm-row{{display:flex;align-items:center;height:20px;margin:2px 0}}
.hm-label{{width:190px;font-size:.72em;color:#2c3e50;text-align:right;padding-right:8px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;flex-shrink:0}}
.hm-bar{{flex:1;position:relative;height:16px;background:#e8f8f5;border-radius:3px;overflow:hidden}}
.hm-drought{{position:absolute;height:100%;border-radius:2px}}
.insights{{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;border-radius:12px;padding:22px;margin:20px 0}}
.insights h3{{margin-bottom:12px;font-size:1.2em}}
.ins-item{{display:flex;gap:10px;margin:10px 0;padding:8px;background:rgba(255,255,255,.08);border-radius:8px;font-size:.9em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>SCORING DROUGHT ANALYSIS</h1>
<div style="font-size:1.1em;opacity:.9">Killinkere — 2026 Season</div>
<div class="sub" id="hdr-sub"></div>
</div>
<div class="filters">
<button class="fbtn active" onclick="pick('All')">All (23)</button>
<button class="fbtn" onclick="pick('ACFL Div 3')">Div 3 (8)</button>
<button class="fbtn" onclick="pick('ACFL Div 7')">Div 7 (7)</button>
<button class="fbtn" onclick="pick('Spring League')">Spring League (5)</button>
<button class="fbtn" onclick="pick('Challenge')">Challenge (3)</button>
</div>
<div class="content">
<div class="cards" id="cards"></div>
<div class="panel"><h3>Scoring Frequency by Game Minute</h3><div class="sub">Higher = more scoring activity. Red zones = drought-prone.</div><canvas id="c1" height="90"></canvas></div>
<div class="g2">
<div class="panel"><h3>Droughts per Game by Phase</h3><canvas id="c2" height="120"></canvas></div>
<div class="panel"><h3>Avg Drought Duration by Phase</h3><canvas id="c3" height="120"></canvas></div>
</div>
<div class="g2">
<div class="panel"><h3>1st Half vs 2nd Half</h3><canvas id="c4" height="120"></canvas></div>
<div class="panel"><h3>Time to First Score</h3><div id="opening-info" style="text-align:center;font-size:.9em;color:#555;margin-bottom:8px;"></div><canvas id="c5" height="120"></canvas></div>
</div>
<div class="panel"><h3>Drought Heatmap — Every Game</h3><div class="sub">Coloured bars show 5+ min droughts positioned on the timeline. Hover for details.</div><div id="heatmap"></div></div>
<div class="panel"><h3>Top 10 Longest Droughts</h3><div id="tbl"></div></div>
<div class="insights" id="insights"></div>
</div>
</div>
<script>
const D={fd_json};
let C={{}};
function pick(f){{
document.querySelectorAll('.fbtn').forEach(b=>b.classList.toggle('active',b.textContent.includes(f==='All'?'All':f)));
render(f);
}}
function render(f){{
const d=D[f];
document.getElementById('hdr-sub').textContent=d.n+' Games • '+Math.round(d.dpg*d.n)+' Droughts (5+min) • Longest: '+d.longest;
document.getElementById('cards').innerHTML=`
<div class="card"><div class="v">${{d.dpg}}</div><div class="l">Droughts/Game (5+min)</div></div>
<div class="card"><div class="v">${{d.avg_sig}}</div><div class="l">Avg Duration</div></div>
<div class="card"><div class="v">${{d.longest}}</div><div class="l">Longest Drought</div></div>
<div class="card"><div class="v">${{d.avg_open}}</div><div class="l">Avg 1st Score</div></div>`;
// Charts
Object.values(C).forEach(c=>c.destroy());C={{}};
const ph=['0-10','10-20','20-30','30-40','40-50','50-60'];
C.c1=new Chart(document.getElementById('c1'),{{type:'bar',data:{{labels:Array.from({{length:65}},(_,i)=>i),datasets:[{{data:d.smoothed,backgroundColor:d.smoothed.map(v=>{{const mx=Math.max(...d.smoothed);const r=mx?v/mx:0;return r<.25?'rgba(231,76,60,.8)':r<.45?'rgba(243,156,18,.7)':'rgba(46,204,113,.7)'}}),borderWidth:0,barPercentage:1,categoryPercentage:1}}]}},options:{{responsive:true,animation:false,scales:{{x:{{ticks:{{maxTicksLimit:13}}}},y:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});
C.c2=new Chart(document.getElementById('c2'),{{type:'bar',data:{{labels:ph,datasets:[{{data:d.phase_per_game,backgroundColor:d.phase_per_game.map(v=>v>=1.2?'rgba(231,76,60,.8)':v>=.8?'rgba(243,156,18,.7)':'rgba(46,204,113,.7)'),borderWidth:0}}]}},options:{{responsive:true,animation:false,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});
C.c3=new Chart(document.getElementById('c3'),{{type:'line',data:{{labels:ph,datasets:[{{data:d.phase_avg_dur,borderColor:'rgba(155,89,182,1)',backgroundColor:'rgba(155,89,182,.15)',borderWidth:3,fill:true,tension:.3,pointRadius:5,pointBackgroundColor:'rgba(155,89,182,1)',pointBorderColor:'#fff',pointBorderWidth:2}}]}},options:{{responsive:true,animation:false,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{display:false}}}}}}}});
C.c4=new Chart(document.getElementById('c4'),{{type:'bar',data:{{labels:['Droughts/Game','Avg Duration (min)'],datasets:[{{label:'1st Half',data:[d.h1_pg,d.h1_avg],backgroundColor:'rgba(231,76,60,.7)'}},{{label:'2nd Half',data:[d.h2_pg,d.h2_avg],backgroundColor:'rgba(52,152,219,.7)'}}]}},options:{{responsive:true,animation:false,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{position:'top'}}}}}}}});
// Opening chart
const op=d.open_slow,ot=d.open_total;
document.getElementById('opening-info').textContent=op+'/'+ot+' games ('+Math.round(ot?op/ot*100:0)+'%) take 5+ min to score';
C.c5=new Chart(document.getElementById('c5'),{{type:'doughnut',data:{{labels:['Under 5 min','5+ min'],datasets:[{{data:[ot-op,op],backgroundColor:['rgba(46,204,113,.7)','rgba(231,76,60,.7)'],borderWidth:2,borderColor:'#fff'}}]}},options:{{responsive:true,animation:false,plugins:{{legend:{{position:'bottom'}}}}}}}});
// Heatmap
let hm='';
d.heatmap.forEach(g=>{{
hm+=`<div class="hm-row"><div class="hm-label">${{g.name}}</div><div class="hm-bar">`;
g.droughts.forEach(dr=>{{
const left=(dr.s/60/65*100).toFixed(1);
const width=(dr.d/60/65*100).toFixed(1);
const dur=dr.d/60;
let col;
if(dur>=15)col='rgba(192,57,43,.9)';else if(dur>=10)col='rgba(231,76,60,.85)';else if(dur>=7)col='rgba(243,156,18,.75)';else col='rgba(241,196,15,.65)';
const tt=Math.floor(dur)+'min ('+Math.floor(dr.s/60)+'-'+Math.floor(dr.e/60)+')';hm+='<div class="hm-drought" title="'+tt+'" style="left:'+left+'%;width:'+width+'%;background:'+col+'"></div>';
}});
hm+=`</div></div>`;
}});
hm+=`<div style="display:flex;gap:12px;justify-content:center;margin-top:10px;font-size:.75em;color:#555">
<span style="display:inline-block;width:12px;height:12px;background:rgba(241,196,15,.65);border-radius:2px;vertical-align:middle"></span> 5-7m
<span style="display:inline-block;width:12px;height:12px;background:rgba(243,156,18,.75);border-radius:2px;vertical-align:middle"></span> 7-10m
<span style="display:inline-block;width:12px;height:12px;background:rgba(231,76,60,.85);border-radius:2px;vertical-align:middle"></span> 10-15m
<span style="display:inline-block;width:12px;height:12px;background:rgba(192,57,43,.9);border-radius:2px;vertical-align:middle"></span> 15+m
<span style="margin-left:15px;border-left:2px dashed rgba(0,0,0,.3);padding-left:8px">| = HT (30 min)</span></div>`;
document.getElementById('heatmap').innerHTML=hm;
// Table
let tbl='<table><thead><tr><th>Duration</th><th>Window</th><th>Half</th><th>Game</th><th>Comp</th></tr></thead><tbody>';
d.top10.forEach(r=>{{
const bc=r.dur>'15:00'?'bd':r.dur>'10:00'?'bw':'bs';
tbl+=`<tr><td><strong>${{r.dur}}</strong></td><td>${{r.window}}</td><td>${{r.half}}</td><td>${{r.game}}</td><td><span class="badge ${{bc}}">${{r.comp}}</span></td></tr>`;
}});
tbl+='</tbody></table>';
document.getElementById('tbl').innerHTML=tbl;
// Insights
const phases=['Opening 10 min','10-20 min','End of 1st half','Start of 2nd half','40-50 min','Final 10 min'];
const worst=d.phase_per_game.indexOf(Math.max(...d.phase_per_game));
document.getElementById('insights').innerHTML=`<h3>Key Insights — ${{f}}</h3>
<div class="ins-item"><span>🔴</span><span><strong>Danger Zone:</strong> ${{phases[worst]}} — ${{d.phase_per_game[worst]}} droughts/game start here</span></div>
<div class="ins-item"><span>🐢</span><span><strong>Slow Starts:</strong> ${{d.open_slow}}/${{d.open_total}} games take 5+ min to register first score</span></div>
<div class="ins-item"><span>📊</span><span><strong>Halves:</strong> 1st half ${{d.h1_pg}} droughts/game (avg ${{d.h1_avg}}m) vs 2nd half ${{d.h2_pg}} droughts/game (avg ${{d.h2_avg}}m)</span></div>
<div class="ins-item"><span>⚡</span><span><strong>Late Game:</strong> Final 10 min avg drought is ${{d.phase_avg_dur[5]}} min — scoring improves under pressure</span></div>`;
}}
render('All');
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body></html>"""

    out = os.path.join(data_dir, 'Killinkere_drought_analysis.html')
    with open(out, 'w') as f:
        f.write(html)
    print(f"Saved: {out}")

if __name__ == '__main__':
    main()
