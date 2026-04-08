(function() {
  // GoatCounter - free, privacy-friendly analytics (no cookies, GDPR-friendly)
  // Sign up at https://www.goatcounter.com and replace YOURSITE below
  var GOATCOUNTER_SITE = 'killinkere'; // change to your GoatCounter site code

  // Only track after auth (don't count the login screen)
  if (localStorage.getItem('kkere_auth') !== 'd6f0e7fc8d7adc7187966c17a4ccbdfc30464ace3dbefda0e638e0e8c5bb1337') return;

  var s = document.createElement('script');
  s.async = true;
  s.dataset.goatcounter = 'https://' + GOATCOUNTER_SITE + '.goatcounter.com/count';
  s.src = '//gc.zgo.at/count.js';
  document.head.appendChild(s);
})();
