#!/usr/bin/env python3
"""Defensive Trends Generator"""
import csv, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def read_csv(f):
    events = []
    with open(f,'r',encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row.get('Team Name'):
                if 'Game Period' in row and 'Period' not in row: row['Period']=row['Game Period']
                events.append(row)
    return events

def read_meta(f):
    meta={}; mf=Path(f).with_suffix('.meta')
    if not mf.exists():
        for c in Path(f).parent.glob('*.meta'):
            if c.stem.replace(' ','')==Path(f).stem.replace(' ',''): mf=c; break
    if mf.exists():
        for line in open(mf):
            if '=' in line: k,v=line.strip().split('=',1); meta[k]=v
    return meta

def generate():
    data_dir=Path(__file__).parent.parent/'data'
    scored=['Point','Goal','2 Points']
    def pts(o): return 3 if o=='Goal' else (2 if o=='2 Points' else 1)
    def rec(gs):
        w=sum(1 for g in gs if g['result']=='W'); d=sum(1 for g in gs if g['result']=='D'); l=sum(1 for g in gs if g['result']=='L')
        return f'{w}W-{d}D-{l}L'

    games=[]
    foul_players=defaultdict(lambda:{'total':0,'def':0,'mid':0,'att':0})

    for f in sorted(data_dir.glob('Killinkere*.csv')):
        meta=read_meta(str(f)); events=read_csv(str(f))
        teams=set(e['Team Name'] for e in events)
        if 'Killinkere' not in teams: continue
        opp=[t for t in teams if t!='Killinkere'][0]
        ke=[e for e in events if e['Team Name']=='Killinkere']
        oe=[e for e in events if e['Team Name']!=  'Killinkere']

        o_sp=[e for e in oe if e.get('Name')=='Shot from play']
        o_sf=[e for e in oe if e.get('Name')=='Scoreable free']
        o_all=o_sp+o_sf
        o_goals=len([s for s in o_all if s['Outcome']=='Goal'])
        o_scored_play=len([s for s in o_sp if s['Outcome'] in scored])
        o_scored_free=len([s for s in o_sf if s['Outcome'] in scored])
        o_total=sum(pts(s['Outcome']) for s in o_all if s['Outcome'] in scored)
        o_acc=round(o_scored_play/len(o_sp)*100,1) if o_sp else 0
        o_wides=len([s for s in o_sp if s['Outcome']=='Wide'])

        o_h1=sum(pts(s['Outcome']) for s in o_all if s.get('Period')=='1' and s['Outcome'] in scored)
        o_h2=sum(pts(s['Outcome']) for s in o_all if s.get('Period')=='2' and s['Outcome'] in scored)

        fc=[e for e in ke if e.get('Name')=='Free conceded']
        fc_def=len([e for e in fc if e.get('Outcome')=='Defensive third'])
        fc_mid=len([e for e in fc if e.get('Outcome')=='Middle third'])
        fc_att=len([e for e in fc if e.get('Outcome')=='Attacking third'])
        pts_from_frees=sum(pts(s['Outcome']) for s in o_sf if s['Outcome'] in scored)

        for e in fc:
            p=e.get('Player','Unknown')
            if p:
                foul_players[p]['total']+=1
                z=e.get('Outcome','')
                if z=='Defensive third': foul_players[p]['def']+=1
                elif z=='Middle third': foul_players[p]['mid']+=1
                elif z=='Attacking third': foul_players[p]['att']+=1

        o_ko=[e for e in oe if e.get('Name')=='Kickout']
        ko_won=['Won clean','Short won','Break won']
        o_ko_ret=len([k for k in o_ko if k['Outcome'] in ko_won])

        k_total=sum(pts(s['Outcome']) for s in [e for e in events if e['Team Name']=='Killinkere' and e.get('Name') in ['Shot from play','Scoreable free'] and e['Outcome'] in scored])
        result='W' if k_total>o_total else ('L' if k_total<o_total else 'D')

        try: date_obj=datetime.strptime(meta.get('date',''),'%d/%m/%Y')
        except: date_obj=datetime.max

        games.append({'opp':opp,'date':meta.get('date',''),'date_obj':date_obj,'result':result,
            'o_total':o_total,'o_goals':o_goals,'o_acc':o_acc,'o_wides':o_wides,
            'o_scored_play':o_scored_play,'o_scored_free':o_scored_free,'o_shots':len(o_sp),
            'o_h1':o_h1,'o_h2':o_h2,
            'fc_total':len(fc),'fc_def':fc_def,'fc_mid':fc_mid,'fc_att':fc_att,
            'pts_from_frees':pts_from_frees,'o_free_att':len(o_sf),
            'o_ko_ret':o_ko_ret,'o_ko_total':len(o_ko)})

    games.sort(key=lambda g:g['date_obj'])
    total=len(games)
    avg_conc=round(sum(g['o_total'] for g in games)/total,1)

    # Patterns
    opp_acc_low=[g for g in games if g['o_acc']<40]
    opp_acc_high=[g for g in games if g['o_acc']>=40]
    pff_low=[g for g in games if g['pts_from_frees']<=3]
    pff_high=[g for g in games if g['pts_from_frees']>3]
    conc_low=[g for g in games if g['o_total']<=12]
    conc_high=[g for g in games if g['o_total']>12]
    fc_low=[g for g in games if g['fc_total']<=10]
    fc_high=[g for g in games if g['fc_total']>10]
    goals_0=[g for g in games if g['o_goals']==0]
    goals_1=[g for g in games if g['o_goals']==1]
    goals_2p=[g for g in games if g['o_goals']>=2]

    labels=json.dumps([f"v {g['opp']}" for g in games])
    conc_data=json.dumps([g['o_total'] for g in games])
    goals_data=json.dumps([g['o_goals'] for g in games])
    acc_data=json.dumps([g['o_acc'] for g in games])
    h1_data=json.dumps([g['o_h1'] for g in games])
    h2_data=json.dumps([g['o_h2'] for g in games])
    fc_data=json.dumps([g['fc_total'] for g in games])
    pff_data=json.dumps([g['pts_from_frees'] for g in games])
    bar_colors=json.dumps(['rgba(46,204,113,0.8)' if g['result']=='W' else ('rgba(231,76,60,0.8)' if g['result']=='L' else 'rgba(243,156,18,0.8)') for g in games])
    bar_borders=json.dumps(['rgba(39,174,96,1)' if g['result']=='W' else ('rgba(192,57,43,1)' if g['result']=='L' else 'rgba(230,126,34,1)') for g in games])

    # Table rows
    trows=''
    for g in games:
        rc='#2ecc71' if g['result']=='W' else ('#e74c3c' if g['result']=='L' else '#f39c12')
        ko_pct=round(g['o_ko_ret']/g['o_ko_total']*100) if g['o_ko_total'] else 0
        trows+=f'<tr><td>{g["date"]}</td><td>v {g["opp"]}</td><td style="color:{rc};font-weight:bold">{g["result"]}</td><td>{g["o_total"]}</td><td>{g["o_goals"]}</td><td>{g["o_scored_play"]}/{g["o_shots"]} ({g["o_acc"]}%)</td><td>{g["o_wides"]}</td><td>{g["o_scored_free"]}/{g["o_free_att"]}</td><td>{g["pts_from_frees"]}</td><td>{g["fc_total"]}</td><td>{g["fc_def"]}/{g["fc_mid"]}/{g["fc_att"]}</td><td>{g["o_h1"]}</td><td>{g["o_h2"]}</td><td>{ko_pct}%</td></tr>\n'

    # Foul table
    foul_sorted=sorted(foul_players.items(),key=lambda x:x[1]['total'],reverse=True)
    foul_rows=''
    for name,d in foul_sorted[:15]:
        foul_rows+=f'<tr><td><strong>{name}</strong></td><td>{d["total"]}</td><td>{d["def"]}</td><td>{d["mid"]}</td><td>{d["att"]}</td></tr>\n'

    html=f'''<!DOCTYPE html>
<html lang="en">
<head><meta name="robots" content="noindex, nofollow">
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Defensive Trends — Killinkere 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#2c3e50,#3498db);padding:20px}}
.container{{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.header{{background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;padding:40px;text-align:center}}
.header h1{{font-size:2.8em;margin-bottom:8px;text-shadow:2px 2px 4px rgba(0,0,0,.3)}}
.header p{{font-size:1.2em;opacity:.85}}
.summary-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:30px}}
.summary-card{{background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;border-radius:14px;padding:20px;text-align:center}}
.summary-card .val{{font-size:2em;font-weight:bold}}.summary-card .lbl{{font-size:.82em;opacity:.85;margin-top:3px}}
.tabs{{display:flex;background:#34495e}}.tab{{flex:1;padding:18px;text-align:center;color:#fff;cursor:pointer;transition:.3s;font-size:1.05em;font-weight:bold}}
.tab:hover{{background:#2c3e50}}.tab.active{{background:#c0392b}}
.tab-content{{display:none;padding:35px}}.tab-content.active{{display:block}}
.pattern-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px;margin-bottom:30px}}
.pattern-card{{border-radius:14px;padding:25px}}.pattern-card h3{{font-size:1.15em;margin-bottom:12px}}
.pattern-card .insight{{font-size:.92em;color:#555;line-height:1.5;margin-bottom:14px}}
.rec{{padding:6px 14px;border-radius:8px;font-weight:bold;font-size:.9em;display:inline-block;margin:4px}}
.rec-good{{background:rgba(46,204,113,.15);color:#27ae60;border:1px solid rgba(46,204,113,.3)}}
.rec-bad{{background:rgba(231,76,60,.15);color:#c0392b;border:1px solid rgba(231,76,60,.3)}}
.pattern-green{{background:linear-gradient(135deg,rgba(46,204,113,.08),rgba(46,204,113,.15));border-left:5px solid #2ecc71}}
.pattern-red{{background:linear-gradient(135deg,rgba(231,76,60,.08),rgba(231,76,60,.15));border-left:5px solid #e74c3c}}
.pattern-blue{{background:linear-gradient(135deg,rgba(52,152,219,.08),rgba(52,152,219,.15));border-left:5px solid #3498db}}
.pattern-gold{{background:linear-gradient(135deg,rgba(243,156,18,.08),rgba(243,156,18,.15));border-left:5px solid #f39c12}}
.chart-box{{background:#fff;border-radius:15px;padding:28px;margin:22px 0;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
.chart-title{{font-size:1.6em;color:#2c3e50;margin-bottom:18px;text-align:center;font-weight:bold}}
table.def-table{{width:100%;border-collapse:collapse;font-size:.85em}}
.def-table th{{background:#34495e;color:#fff;padding:10px 8px;text-align:center;white-space:nowrap;cursor:pointer}}
.def-table th:hover{{background:#2c3e50}}.def-table td{{padding:8px;border-bottom:1px solid #ecf0f1;text-align:center}}
.def-table tr:hover{{background:#f0f4ff}}.def-table tr:nth-child(even){{background:#f8f9fa}}
.footer{{text-align:center;color:rgba(255,255,255,.7);margin-top:20px;font-size:.9em}}
</style></head><body>
<div class="container">
<div class="header">
<h1>🛡️ DEFENSIVE TRENDS</h1>
<p>Killinkere GAA — 2026 Season · {total} Games Analyzed</p>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('patterns')">🔍 Patterns</div>
<div class="tab" onclick="showTab('charts')">📈 Charts</div>
<div class="tab" onclick="showTab('fouls')">🟨 Fouls & Frees</div>
<div class="tab" onclick="showTab('table')">📋 Full Table</div>
</div>

<div id="patterns" class="tab-content active">
<div class="summary-row">
<div class="summary-card"><div class="val">{avg_conc}</div><div class="lbl">Avg Pts Conceded</div></div>
<div class="summary-card"><div class="val">{sum(g['o_goals'] for g in games)}</div><div class="lbl">Total Goals Conc.</div></div>
<div class="summary-card"><div class="val">{round(sum(g['fc_total'] for g in games)/total,1)}</div><div class="lbl">Avg Frees Conc.</div></div>
<div class="summary-card"><div class="val">{sum(g['pts_from_frees'] for g in games)}</div><div class="lbl">Total Pts from Frees</div></div>
</div>

<h2 style="color:#2c3e50;text-align:center;margin:20px 0;font-size:1.7em">🔍 Defensive Patterns</h2>
<div class="pattern-grid">

<div class="pattern-card pattern-green">
<h3>🎯 Force Poor Shooting (&lt;40% Opp Accuracy)</h3>
<div class="insight">The strongest defensive predictor. When opposition accuracy is held below 40%: {rec(opp_acc_low)}. When they shoot 40%+: {rec(opp_acc_high)}. Making them take difficult shots from distance is the best defence.</div>
<div><span class="rec rec-good">&lt;40%: {rec(opp_acc_low)}</span><span class="rec rec-bad">≥40%: {rec(opp_acc_high)}</span></div>
</div>

<div class="pattern-card pattern-red">
<h3>🟨 Points Conceded from Frees</h3>
<div class="insight">When opposition score ≤3pts from frees: {rec(pff_low)}. When they score 4+: {rec(pff_high)}. The Arva draw (10pts from frees) and Denn Div 3 loss (10pts from frees) are the standout examples of fouling costing results.</div>
<div><span class="rec rec-good">≤3pts: {rec(pff_low)}</span><span class="rec rec-bad">&gt;3pts: {rec(pff_high)}</span></div>
</div>

<div class="pattern-card pattern-blue">
<h3>🔒 Keep It Tight (≤12pts Conceded)</h3>
<div class="insight">Unbeaten when holding opposition to 12 points or fewer: {rec(conc_low)}. When conceding 13+: {rec(conc_high)}. The 12-point mark is the defensive threshold.</div>
<div><span class="rec rec-good">≤12pts: {rec(conc_low)}</span><span class="rec rec-bad">&gt;12pts: {rec(conc_high)}</span></div>
</div>

<div class="pattern-card pattern-gold">
<h3>🥅 Goals Conceded</h3>
<div class="insight">0 goals conceded: {rec(goals_0)}. 1 goal: {rec(goals_1)}. 2+ goals: {rec(goals_2p)}. Goals conceded doesn't cleanly predict results — Killinkere have won games conceding 3 goals (v Drung, v Kill Shamrocks). But the Denn Div 3 loss (3 goals) shows it can be fatal against quality opposition.</div>
<div><span class="rec rec-good">0 goals: {rec(goals_0)}</span><span class="rec rec-good">1 goal: {rec(goals_1)}</span><span class="rec rec-bad">2+ goals: {rec(goals_2p)}</span></div>
</div>

<div class="pattern-card pattern-green">
<h3>🤐 Discipline (≤10 Frees Conceded)</h3>
<div class="insight">Unbeaten when conceding 10 or fewer frees: {rec(fc_low)}. When conceding 11+: {rec(fc_high)}. Fewer fouls = fewer scoring chances for the opposition and less pressure on the defence.</div>
<div><span class="rec rec-good">≤10: {rec(fc_low)}</span><span class="rec rec-bad">&gt;10: {rec(fc_high)}</span></div>
</div>

<div class="pattern-card pattern-blue">
<h3>📊 Where Conceded Scores Come From</h3>
<div class="insight">Across {total} games: {round(sum(g['o_scored_play'] for g in games)*100/max(1,sum(g['o_scored_play']+g['o_scored_free'] for g in games)))}% of opposition scores come from play, {round(sum(g['o_scored_free'] for g in games)*100/max(1,sum(g['o_scored_play']+g['o_scored_free'] for g in games)))}% from frees. {sum(g['pts_from_frees'] for g in games)} points conceded from dead balls across the season — that's {round(sum(g['pts_from_frees'] for g in games)/sum(g['o_total'] for g in games)*100)}% of all points conceded.</div>
</div>

</div>
</div>

<div id="charts" class="tab-content">
<div class="chart-box"><div class="chart-title">📊 Points Conceded per Game</div><canvas id="concChart"></canvas></div>
<div class="chart-box"><div class="chart-title">🥅 Goals Conceded per Game</div><canvas id="goalsChart"></canvas></div>
<div class="chart-box"><div class="chart-title">🎯 Opposition Shot Accuracy</div><canvas id="accChart"></canvas></div>
<div class="chart-box"><div class="chart-title">⏱️ Conceded by Half</div><canvas id="halvesChart"></canvas></div>
<div class="chart-box"><div class="chart-title">🟨 Frees Conceded & Points from Frees</div><canvas id="freesChart"></canvas></div>
</div>

<div id="fouls" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">🟨 Frees Conceded by Player (Season)</h2>
<table class="def-table">
<thead><tr><th>Player</th><th>Total</th><th>Defensive 3rd</th><th>Middle 3rd</th><th>Attacking 3rd</th></tr></thead>
<tbody>{foul_rows}</tbody>
</table>
</div>

<div id="table" class="tab-content">
<h2 style="color:#2c3e50;text-align:center;margin-bottom:18px;font-size:1.7em">📋 Defensive Game-by-Game</h2>
<div style="overflow-x:auto">
<table class="def-table" id="defTable">
<thead><tr><th>Date</th><th>Opp</th><th>Res</th><th>Conc</th><th>Goals</th><th>Opp Acc (play)</th><th>Wides</th><th>Frees Scored</th><th>Pts from Frees</th><th>Frees Conc</th><th>D/M/A</th><th>1H</th><th>2H</th><th>Opp KO Ret</th></tr></thead>
<tbody>{trows}</tbody>
</table></div>
</div>

</div>
<div class="footer">Killinkere GAA · Defensive Trends · 2026</div>

<script>
function showTab(t){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById(t).classList.add('active');event.target.classList.add('active')}}
const L={labels},C={bar_colors},B={bar_borders};
const green='rgba(46,204,113,0.8)',greenB='rgba(39,174,96,1)',red='rgba(231,76,60,0.8)',redB='rgba(192,57,43,1)',blue='rgba(52,152,219,0.8)',blueB='rgba(41,128,185,1)',orange='rgba(243,156,18,0.8)',orangeB='rgba(230,126,34,1)';
new Chart(document.getElementById('concChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Pts Conceded',data:{conc_data},backgroundColor:C,borderColor:B,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}}}}}},plugins:[{{id:'t',afterDatasetsDraw(c){{const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=c;const yp=y.getPixelForValue(12);ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='rgba(46,204,113,0.6)';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(left,yp);ctx.lineTo(right,yp);ctx.stroke();ctx.fillStyle='rgba(46,204,113,0.8)';ctx.font='bold 10px Arial';ctx.textAlign='right';ctx.fillText('12pt threshold',right,yp-4);ctx.restore()}}}}]}});
new Chart(document.getElementById('goalsChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Goals',data:{goals_data},backgroundColor:red,borderColor:redB,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}}}}}});
new Chart(document.getElementById('accChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Opp Accuracy %',data:{acc_data},backgroundColor:C,borderColor:B,borderWidth:2}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,max:70,ticks:{{callback:v=>v+'%'}}}}}}}},plugins:[{{id:'a',afterDatasetsDraw(c){{const{{ctx,chartArea:{{left,right}},scales:{{y}}}}=c;const yp=y.getPixelForValue(40);ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='rgba(231,76,60,0.6)';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(left,yp);ctx.lineTo(right,yp);ctx.stroke();ctx.fillStyle='rgba(231,76,60,0.8)';ctx.font='bold 10px Arial';ctx.textAlign='right';ctx.fillText('40% danger line',right,yp-4);ctx.restore()}}}}]}});
new Chart(document.getElementById('halvesChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'1st Half',data:{h1_data},backgroundColor:orange,borderColor:orangeB,borderWidth:2}},{{label:'2nd Half',data:{h2_data},backgroundColor:blue,borderColor:blueB,borderWidth:2}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{display:true,position:'top'}}}}}}}});
new Chart(document.getElementById('freesChart'),{{type:'bar',data:{{labels:L,datasets:[{{label:'Frees Conceded',data:{fc_data},backgroundColor:orange,borderColor:orangeB,borderWidth:2}},{{label:'Pts from Frees',data:{pff_data},backgroundColor:red,borderColor:redB,borderWidth:2}}]}},options:{{responsive:true,scales:{{y:{{beginAtZero:true}}}},plugins:{{legend:{{display:true,position:'top'}}}}}}}});
document.querySelectorAll('.def-table th').forEach((th,i)=>{{let asc=true;th.addEventListener('click',()=>{{const tbody=th.closest('table').querySelector('tbody');const rows=Array.from(tbody.querySelectorAll('tr'));rows.sort((a,b)=>{{let av=a.children[i].textContent.replace(/[m%]/g,'').trim();let bv=b.children[i].textContent.replace(/[m%]/g,'').trim();if(!isNaN(parseFloat(av))&&!isNaN(parseFloat(bv)))return asc?av-bv:bv-av;return asc?av.localeCompare(bv):bv.localeCompare(av)}});rows.forEach(r=>tbody.appendChild(r));asc=!asc}});}});
</script>
<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>
</body></html>'''

    output=Path(__file__).parent.parent/'analysis'/'defensive_trends.html'
    with open(output,'w',encoding='utf-8') as f: f.write(html)
    print(f"✅ Generated: {output}")

if __name__=="__main__": generate()
