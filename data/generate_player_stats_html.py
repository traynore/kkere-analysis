#!/usr/bin/env python3
"""Generate HTML player shooting stats with play and frees split."""
import csv, os, glob, json, difflib
from collections import defaultdict

def parse_time(t):
    parts = t.strip().split(':')
    if len(parts)==3: return int(parts[0])*3600+int(parts[1])*60+int(parts[2])
    elif len(parts)==2: return int(parts[0])*60+int(parts[1])
    return 0

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

def main():
    data_dir = '/Users/hz448961/DevOps/test/data'
    csv_files = sorted(glob.glob(os.path.join(data_dir,'Killinkere*.csv')))

    empty = lambda: {'goals':0,'points':0,'2pts':0,'wides':0,'shorts':0,'other':0,'shots':0}
    players = defaultdict(lambda: defaultdict(lambda: {'play': empty(), 'free': empty()}))
    player_games = defaultdict(lambda: defaultdict(set))

    for fp in csv_files:
        game_name = os.path.basename(fp).replace('.csv','')
        meta = load_meta(fp)
        comp = classify(meta.get('competition',''))
        try:
            for enc in ['utf-8','utf-8-sig','latin-1','cp1252']:
                try:
                    with open(fp,'r',encoding=enc) as f: content = f.read()
                    break
                except: continue
            lines = content.replace('\r\n','\n').replace('\r','\n').split('\n')
            clean = []
            for l in lines:
                if l.strip()=='' or l.startswith('='): break
                clean.append(l)
            if not clean: continue
            for row in csv.DictReader(clean):
                if row.get('Team Name','') != 'Killinkere': continue
                shot_type = row.get('Name','')
                if shot_type not in ['Shot from play','Scoreable free']: continue
                player = row.get('Player','').strip()
                if not player: continue
                outcome = row.get('Outcome','')
                key = 'free' if shot_type == 'Scoreable free' else 'play'
                p = players[player][comp][key]
                p['shots'] += 1
                player_games[player][comp].add(game_name)
                if outcome == 'Goal': p['goals'] += 1
                elif outcome == 'Point': p['points'] += 1
                elif outcome == '2 Points': p['2pts'] += 1
                elif outcome == 'Wide': p['wides'] += 1
                elif outcome == 'Short': p['shorts'] += 1
                else: p['other'] += 1
        except: pass

    all_comps = ['All','ACFL Div 3','ACFL Div 7','Spring League','Challenge']
    filter_data = {}
    for filt in all_comps:
        player_list = []
        for player, comps in players.items():
            tp = empty()
            tf = empty()
            games = 0
            for comp, data in comps.items():
                if filt != 'All' and comp != filt: continue
                for k in ['goals','points','2pts','wides','shorts','other','shots']:
                    tp[k] += data['play'][k]
                    tf[k] += data['free'][k]
                games += len(player_games[player][comp])
            total_shots = tp['shots'] + tf['shots']
            if total_shots == 0: continue
            play_scored = tp['goals'] + tp['points'] + tp['2pts']
            free_scored = tf['goals'] + tf['points'] + tf['2pts']
            player_list.append({
                'name': player, 'games': games,
                'p_shots': tp['shots'], 'p_scored': play_scored,
                'p_acc': round(play_scored*100/tp['shots']) if tp['shots'] else 0,
                'p_goals': tp['goals'], 'p_points': tp['points'], 'p_twos': tp['2pts'],
                'p_wides': tp['wides'], 'p_shorts': tp['shorts'], 'p_other': tp['other'],
                'f_shots': tf['shots'], 'f_scored': free_scored,
                'f_acc': round(free_scored*100/tf['shots']) if tf['shots'] else 0,
                'f_goals': tf['goals'], 'f_points': tf['points'], 'f_twos': tf['2pts'],
                'f_wides': tf['wides'], 'f_shorts': tf['shorts'], 'f_other': tf['other'],
            })
        player_list.sort(key=lambda x: x['p_shots'], reverse=True)
        filter_data[filt] = player_list

    fd_json = json.dumps(filter_data)

    # Build HTML using plain string (no f-string)
    CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}
.ctr{max-width:1400px;margin:0 auto;background:#fff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.hdr{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:30px;text-align:center;border-radius:20px 20px 0 0}
.hdr h1{font-size:2.2em;margin-bottom:6px}.hdr .sub{opacity:.8;margin-top:8px}
.flt{display:flex;justify-content:center;gap:8px;padding:16px;background:#34495e;flex-wrap:wrap}
.fb{padding:9px 18px;border-radius:20px;border:2px solid #fff;background:transparent;color:#fff;font-weight:bold;font-size:.85em;cursor:pointer;transition:.3s}
.fb:hover{background:rgba(255,255,255,.15)}.fb.active{background:#2a5298;border-color:#4ecdc4;color:#4ecdc4}
.cnt{padding:25px 35px}
.tbl-wrap{overflow-x:auto;margin:15px 0}
table{width:100%;border-collapse:collapse;min-width:800px}
th{background:#34495e;color:#fff;padding:11px 8px;text-align:left;font-size:.8em;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{background:#2c3e50}th.fh{background:#1a5276}th.fh:hover{background:#154360}
td{padding:9px 8px;border-bottom:1px solid #ecf0f1;font-size:.82em}
tr:hover{background:#e8f4fd}tr:nth-child(even){background:#f8f9fa}
.acc-bar{width:100%;height:22px;background:#ecf0f1;border-radius:11px;overflow:hidden;min-width:80px}
.acc-fill{height:100%;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:.72em;font-weight:bold}
.score-bar{display:flex;height:18px;border-radius:9px;overflow:hidden;min-width:100px}
.sb-g{background:#27ae60}.sb-p{background:#2ecc71}.sb-2{background:#f39c12}
.sb-w{background:#e74c3c}.sb-s{background:#c0392b}.sb-o{background:#95a5a6}
.legend{display:flex;gap:12px;justify-content:center;margin:15px 0;flex-wrap:wrap;font-size:.78em}
.legend span{display:flex;align-items:center;gap:4px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block}
.panel{background:#fff;border-radius:14px;padding:22px;margin:20px 0;box-shadow:0 3px 6px rgba(0,0,0,.08);border:1px solid #ecf0f1}
.panel h3{font-size:1.2em;color:#2c3e50;margin-bottom:5px;text-align:center}
.panel .sub{font-size:.82em;color:#7f8c8d;text-align:center;margin-bottom:12px}
.tag{display:inline-block;padding:3px 10px;border-radius:10px;font-size:.7em;font-weight:bold;margin-left:8px}
.tag-p{background:#d4edda;color:#155724}.tag-f{background:#d6eaf8;color:#1a5276}"""

    JS = """var D=__DATA__;
var cur='All';
var ss={p:{c:2,a:false},f:{c:2,a:false}};
function pick(f){cur=f;document.querySelectorAll('.fb').forEach(function(b){b.classList.toggle('active',b.textContent.indexOf(f==='All'?'All':f)>=0);});render();}
function srt(t,c){if(ss[t].c===c){ss[t].a=!ss[t].a;}else{ss[t].c=c;ss[t].a=false;}render();}
function ab(acc){var col=acc>=65?'#27ae60':acc>=50?'#f39c12':'#e74c3c';return '<div class="acc-bar"><div class="acc-fill" style="width:'+acc+'%;background:'+col+'">'+acc+'%</div></div>';}
function mkb(g,p,t,w,s,o,tot){var h='<div class="score-bar">';if(g)h+='<div class="sb-g" style="width:'+Math.round(g*100/tot)+'%" title="'+g+' goals"></div>';if(p)h+='<div class="sb-p" style="width:'+Math.round(p*100/tot)+'%" title="'+p+' points"></div>';if(t)h+='<div class="sb-2" style="width:'+Math.round(t*100/tot)+'%" title="'+t+' 2pts"></div>';if(w)h+='<div class="sb-w" style="width:'+Math.round(w*100/tot)+'%" title="'+w+' wides"></div>';if(s)h+='<div class="sb-s" style="width:'+Math.round(s*100/tot)+'%" title="'+s+' shorts"></div>';if(o)h+='<div class="sb-o" style="width:'+Math.round(o*100/tot)+'%" title="'+o+' other"></div>';return h+'</div>';}
function render(){
var data=D[cur];
var tPS=0,tPSc=0,tFS=0,tFSc=0;
data.forEach(function(p){tPS+=p.p_shots;tPSc+=p.p_scored;tFS+=p.f_shots;tFSc+=p.f_scored;});
var pAcc=tPS?Math.round(tPSc*100/tPS):0;
var fAcc=tFS?Math.round(tFSc*100/tFS):0;
document.getElementById('hdr-sub').textContent=data.length+' players | From play: '+tPSc+'/'+tPS+' ('+pAcc+'%) | Frees: '+tFSc+'/'+tFS+' ('+fAcc+'%)';
var pK=['name','games','p_shots','p_scored','p_missed','p_acc','p_goals','p_points','p_twos','p_wides','p_shorts'];
var pd=data.filter(function(p){return p.p_shots>0;}).slice();
pd.forEach(function(p){p.p_missed=p.p_wides+p.p_shorts+p.p_other;});
pd.sort(function(a,b){var k=pK[ss.p.c];var av=a[k],bv=b[k];if(typeof av==='string')return ss.p.a?av.localeCompare(bv):bv.localeCompare(av);return ss.p.a?av-bv:bv-av;});
var h='';
pd.forEach(function(p){
h+='<tr><td><strong>'+p.name+'</strong></td><td>'+p.games+'</td><td>'+p.p_shots+'</td>';
h+='<td style="color:#27ae60;font-weight:bold">'+p.p_scored+'</td>';
h+='<td style="color:#e74c3c">'+p.p_missed+'</td>';
h+='<td>'+ab(p.p_acc)+'</td>';
h+='<td>'+p.p_goals+'</td><td>'+p.p_points+'</td><td>'+p.p_twos+'</td>';
h+='<td>'+p.p_wides+'</td><td>'+p.p_shorts+'</td>';
h+='<td>'+mkb(p.p_goals,p.p_points,p.p_twos,p.p_wides,p.p_shorts,p.p_other,p.p_shots)+'</td></tr>';
});
document.getElementById('tp').innerHTML=h;
var fK=['name','games','f_shots','f_scored','f_missed','f_acc','f_goals','f_points','f_twos','f_wides','f_shorts'];
var fd=data.filter(function(p){return p.f_shots>0;}).slice();
fd.forEach(function(p){p.f_missed=p.f_wides+p.f_shorts+p.f_other;});
fd.sort(function(a,b){var k=fK[ss.f.c];var av=a[k],bv=b[k];if(typeof av==='string')return ss.f.a?av.localeCompare(bv):bv.localeCompare(av);return ss.f.a?av-bv:bv-av;});
var fh='';
fd.forEach(function(p){
fh+='<tr><td><strong>'+p.name+'</strong></td><td>'+p.games+'</td><td>'+p.f_shots+'</td>';
fh+='<td style="color:#27ae60;font-weight:bold">'+p.f_scored+'</td>';
fh+='<td style="color:#e74c3c">'+p.f_missed+'</td>';
fh+='<td>'+ab(p.f_acc)+'</td>';
fh+='<td>'+p.f_goals+'</td><td>'+p.f_points+'</td><td>'+p.f_twos+'</td>';
fh+='<td>'+p.f_wides+'</td><td>'+p.f_shorts+'</td>';
fh+='<td>'+mkb(p.f_goals,p.f_points,p.f_twos,p.f_wides,p.f_shorts,p.f_other,p.f_shots)+'</td></tr>';
});
document.getElementById('tf').innerHTML=fh;
}
render();"""

    JS = JS.replace('__DATA__', fd_json)

    BODY = """<div class="ctr">
<div class="hdr"><h1>PLAYER SHOOTING STATS</h1>
<div style="font-size:1.1em">Killinkere &mdash; 2026 Season</div>
<div class="sub" id="hdr-sub"></div></div>
<div class="flt">
<button class="fb active" onclick="pick('All')">All (23 games)</button>
<button class="fb" onclick="pick('ACFL Div 3')">Div 3 (8)</button>
<button class="fb" onclick="pick('ACFL Div 7')">Div 7 (7)</button>
<button class="fb" onclick="pick('Spring League')">Spring League (5)</button>
<button class="fb" onclick="pick('Challenge')">Challenge (3)</button>
</div>
<div class="cnt">
<div class="panel"><h3>From Play <span class="tag tag-p">OPEN PLAY</span></h3>
<div class="sub">Click column headers to sort. Bar shows scored vs missed breakdown.</div>
<div class="legend"><span><i style="background:#27ae60"></i> Goals</span><span><i style="background:#2ecc71"></i> Points</span><span><i style="background:#f39c12"></i> 2-Pointers</span><span><i style="background:#e74c3c"></i> Wides</span><span><i style="background:#c0392b"></i> Shorts</span><span><i style="background:#95a5a6"></i> Other</span></div>
<div class="tbl-wrap"><table><thead><tr>
<th onclick="srt('p',0)">Player</th><th onclick="srt('p',1)">Games</th><th onclick="srt('p',2)">Shots</th><th onclick="srt('p',3)">Scored</th><th onclick="srt('p',4)">Missed</th><th onclick="srt('p',5)">Accuracy</th><th onclick="srt('p',6)">Goals</th><th onclick="srt('p',7)">Pts</th><th onclick="srt('p',8)">2Pts</th><th onclick="srt('p',9)">Wides</th><th onclick="srt('p',10)">Shorts</th><th>Breakdown</th>
</tr></thead><tbody id="tp"></tbody></table></div></div>
<div class="panel"><h3>From Frees <span class="tag tag-f">PLACED BALLS</span></h3>
<div class="sub">Scoreable frees only. Players with 0 frees are hidden.</div>
<div class="tbl-wrap"><table><thead><tr>
<th class="fh" onclick="srt('f',0)">Player</th><th class="fh" onclick="srt('f',1)">Games</th><th class="fh" onclick="srt('f',2)">Taken</th><th class="fh" onclick="srt('f',3)">Scored</th><th class="fh" onclick="srt('f',4)">Missed</th><th class="fh" onclick="srt('f',5)">Accuracy</th><th class="fh" onclick="srt('f',6)">Goals</th><th class="fh" onclick="srt('f',7)">Pts</th><th class="fh" onclick="srt('f',8)">2Pts</th><th class="fh" onclick="srt('f',9)">Wides</th><th class="fh" onclick="srt('f',10)">Shorts</th><th class="fh">Breakdown</th>
</tr></thead><tbody id="tf"></tbody></table></div></div>
</div></div>"""

    html = '<!DOCTYPE html>\n<html lang="en">\n<head><meta name="robots" content="noindex, nofollow">\n'
    html += '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>Killinkere Player Shooting Stats</title>\n'
    html += '<style>\n' + CSS + '\n</style>\n</head>\n<body>\n'
    html += BODY + '\n'
    html += '<script>\n' + JS + '\n</script>\n'
    html += '<script src="../nav.js"></script><script src="../auth.js"></script><script src="../analytics.js"></script>\n'
    html += '</body></html>'

    out = os.path.join(data_dir, 'Killinkere_player_shooting.html')
    with open(out, 'w') as f:
        f.write(html)
    print("Saved: " + out)

if __name__ == '__main__':
    main()
