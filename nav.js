(function() {
  var sections = [
    {heading:'All Games', games:[
      {label:'📊 All Games Dashboard', file:'ALL_GAMES_FULL.html'}
    ]},
    {heading:'🏆 Ulster Spring League', games:[
      {label:'v Clones (W) 1-14 to 1-12', file:'Killinkere 1 - 14 v 1 - 12 Clones_FULL_infographic.html'},
      {label:'v Denn (W) 3-11 to 1-13', file:'Killinkere 3 - 11 v 1 - 13 Denn_FULL_infographic.html'},
      {label:'v Pearse OG (W) 3-14 to 1-10', file:'Killinkere 3 - 14 v 1 - 10 Pearse OG_FULL_infographic.html'},
      {label:'v Liatroim (W) 4-10 to 2-8', file:'Killinkere 4 - 10 v 2 - 8 Liatroim_FULL_infographic.html'},
      {label:'v Greenlough (L) 0-8 to 0-13', file:'Killinkere 0 - 8 v 0 - 13 Greenlough_FULL_infographic.html'}
    ]},
    {heading:'⚔️ Challenge Matches', games:[
      {label:'v Aughadrumsee (W) 4-9 to 0-12', file:'Killinkere 4 - 9 v 0 - 12 Aughadrumsee_FULL_infographic.html'},
      {label:'v Ballymahon (W) 4-16 to 2-6', file:'Killinkere 4 - 16 v 2 - 6 Ballymahon_FULL_infographic.html'},
      {label:'v Drung (W) 2-13 to 3-7', file:'Killinkere 2 - 13 v 3 - 7 Drung_FULL_infographic.html'}
    ]},
    {heading:'📋 ACFL Division 3', games:[
      {label:'v Denn (L) 4-10 to 3-20', file:'Killinkere 4 - 10 v 3 - 20 Denn_FULL_infographic.html'}
    ]},
    {heading:'📋 ACFL Reserve League', games:[
      {label:'v Arva (D) 1-13 to 1-13', file:'Killinkere 1 - 13 v 1 - 13 Arva_FULL_infographic.html'}
    ]}
  ];

  var isGamesDir = location.pathname.indexOf('/games/') !== -1;
  var isAnalysisDir = location.pathname.indexOf('/analysis/') !== -1;
  var prefix = isGamesDir ? '' : (isAnalysisDir ? '../games/' : 'games/');
  var homeHref = isGamesDir || isAnalysisDir ? '../index.html' : 'index.html';
  var currentFile = location.pathname.split('/').pop();

  var nav = document.createElement('div');
  nav.id = 'floating-nav';
  nav.innerHTML =
    '<div style="position:fixed;bottom:20px;right:20px;z-index:9999;font-family:Segoe UI,sans-serif;display:flex;gap:8px;align-items:flex-end">' +
      '<a href="' + homeHref + '" style="background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;text-decoration:none;padding:12px 20px;border-radius:30px;font-weight:bold;box-shadow:0 4px 15px rgba(0,0,0,.3);font-size:.95em;white-space:nowrap">🏠 Match Hub</a>' +
      '<div style="position:relative">' +
        '<button id="game-toggle" style="background:linear-gradient(135deg,#27ae60,#2ecc71);color:#fff;border:none;padding:12px 20px;border-radius:30px;font-weight:bold;box-shadow:0 4px 15px rgba(0,0,0,.3);font-size:.95em;cursor:pointer;white-space:nowrap">🏐 Games ▾</button>' +
        '<div id="game-menu" style="display:none;position:absolute;bottom:50px;right:0;background:#fff;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.3);min-width:290px;max-height:70vh;overflow-y:auto;padding:6px 0"></div>' +
      '</div>' +
    '</div>';
  document.body.appendChild(nav);

  var menu = document.getElementById('game-menu');
  sections.forEach(function(section, si) {
    if (si > 0) {
      var hr = document.createElement('div');
      hr.style.cssText = 'height:1px;background:#e0e0e0;margin:4px 0';
      menu.appendChild(hr);
    }
    var h = document.createElement('div');
    h.textContent = section.heading;
    h.style.cssText = 'padding:8px 16px 4px;font-size:.75em;font-weight:bold;color:#888;text-transform:uppercase;letter-spacing:.5px';
    menu.appendChild(h);

    section.games.forEach(function(g) {
      var isCurrent = currentFile === g.file;
      var a = document.createElement('a');
      a.href = prefix + g.file;
      a.textContent = g.label;
      a.style.cssText = 'display:block;padding:8px 16px;text-decoration:none;color:' + (isCurrent ? '#27ae60' : '#2c3e50') + ';font-size:.88em;font-weight:' + (isCurrent ? 'bold' : 'normal') + ';border-left:3px solid ' + (isCurrent ? '#27ae60' : 'transparent');
      a.onmouseover = function() { this.style.background = '#f0f0f0'; };
      a.onmouseout = function() { this.style.background = 'none'; };
      menu.appendChild(a);
    });
  });

  var toggle = document.getElementById('game-toggle');
  toggle.addEventListener('click', function(e) {
    e.stopPropagation();
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  });
  document.addEventListener('click', function() { menu.style.display = 'none'; });
})();
