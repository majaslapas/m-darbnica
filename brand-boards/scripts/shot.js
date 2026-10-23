let pw;
try { pw = require('playwright'); } catch (e) { pw = require('/opt/node22/lib/node_modules/playwright'); }
const { chromium } = pw;
(async () => {
  const [,, out, w, h, ...files] = process.argv;
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: +w, height: +h } });
  for (const f of files) {
    await p.goto('file://' + f, { waitUntil: 'load' });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(600);
    const name = f.split('/').pop().replace('.html', '.png');
    await p.screenshot({ path: out + '/' + name });
    console.log(out + '/' + name);
  }
  await b.close();
})();
