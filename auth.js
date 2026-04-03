(function() {
  var HASH = 'd6f0e7fc8d7adc7187966c17a4ccbdfc30464ace3dbefda0e638e0e8c5bb1337';
  var KEY = 'kkere_auth';

  if (localStorage.getItem(KEY) === HASH) return;

  async function sha256(msg) {
    var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(msg));
    return Array.from(new Uint8Array(buf)).map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
  }

  document.body.style.display = 'none';

  var overlay = document.createElement('div');
  overlay.innerHTML =
    '<div style="position:fixed;inset:0;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;z-index:99999;font-family:Segoe UI,sans-serif">' +
      '<div style="background:#fff;padding:40px;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.3);text-align:center;max-width:360px;width:90%">' +
        '<div style="font-size:2em;margin-bottom:8px">🏐</div>' +
        '<h2 style="color:#1e3c72;margin:0 0 6px">Killinkere GAA</h2>' +
        '<p style="color:#666;font-size:.9em;margin:0 0 20px">Squad access only</p>' +
        '<input id="authPw" type="password" placeholder="Enter password" style="width:100%;padding:12px;border:2px solid #ddd;border-radius:8px;font-size:1em;box-sizing:border-box">' +
        '<button id="authBtn" style="width:100%;margin-top:12px;padding:12px;background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;border:none;border-radius:8px;font-size:1em;font-weight:bold;cursor:pointer">Enter</button>' +
        '<p id="authErr" style="color:#e74c3c;margin:10px 0 0;font-size:.85em;display:none">Incorrect password</p>' +
      '</div>' +
    '</div>';
  document.documentElement.appendChild(overlay);

  async function tryAuth() {
    var h = await sha256(document.getElementById('authPw').value);
    if (h === HASH) {
      localStorage.setItem(KEY, HASH);
      overlay.remove();
      document.body.style.display = '';
    } else {
      document.getElementById('authErr').style.display = 'block';
      document.getElementById('authPw').value = '';
    }
  }

  document.getElementById('authBtn').addEventListener('click', tryAuth);
  document.getElementById('authPw').addEventListener('keydown', function(e) { if (e.key === 'Enter') tryAuth(); });
})();
