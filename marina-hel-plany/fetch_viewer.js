const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const seen = [];
  p.on('response', async r => {
    const u = r.url();
    const ct = (r.headers()['content-type'] || '');
    if (ct.includes('json')) {
      let n = 0;
      try { const t = await r.text(); n = t.length; if (u.includes('apartments')) fs.writeFileSync('data/viewer.json', t); } catch (e) {}
      seen.push(r.status() + ' ' + n + ' ' + u.slice(0, 160));
    }
  });
  try { await p.goto('https://allinone.prod.resimo.io/eurostyl/marina-hel-apartamenty/', { waitUntil: 'networkidle', timeout: 90000 }); } catch (e) { console.log('goto', e.message.slice(0, 200)); }
  await p.waitForTimeout(8000);
  console.log(seen.join('\n'));
  
  await b.close();
})();
