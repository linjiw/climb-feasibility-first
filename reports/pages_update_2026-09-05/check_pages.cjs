const { chromium } = require('/tmp/climb-pages-review/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({executablePath:'/usr/bin/google-chrome', headless:true, args:['--no-sandbox','--disable-gpu']});
  const results = [];
  for (const theme of ['light', 'dark']) {
    for (const width of [390, 1440]) {
      const page = await browser.newPage({viewport:{width,height:1000},colorScheme:theme, deviceScaleFactor:1});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      for (const file of ['relative-progress.html','index.html','segment-native.html']) {
        await page.goto('http://127.0.0.1:8766/'+file,{waitUntil:'networkidle'});
        const check = await page.evaluate(() => ({
          width:innerWidth, scrollWidth:document.documentElement.scrollWidth,
          images:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src),
          h1:document.querySelector('h1')?.textContent,
          links:[...document.querySelectorAll('a[href],link[rel=stylesheet],img[src]')].map(e=>e.getAttribute('href')||e.getAttribute('src')).filter(h=>h&&!h.startsWith('data:')),
        }));
        const failures = [];
        for (const link of check.links) {
          if (/^(https?:|mailto:)/.test(link)) continue;
          const parsed=new URL(link,'http://127.0.0.1:8766/'+file);
          const local=path.join(process.cwd(),'docs',decodeURIComponent(parsed.pathname));
          if (!fs.existsSync(local)) failures.push('Missing file: '+link);
          else if (parsed.hash && local.endsWith('.html')) {
            const text=fs.readFileSync(local,'utf8');
            if (!text.includes('id="'+parsed.hash.slice(1)+'"')&&!text.includes("id='"+parsed.hash.slice(1)+"'")) failures.push('Missing anchor: '+link);
          }
        }
        if (file==='relative-progress.html'||(file==='index.html'&&theme==='light')) {
          await page.screenshot({path:`reports/pages_update_2026-09-05/${file.replace('.html','')}_${width}_${theme}.png`});
        }
        if(file==='relative-progress.html'&&width===1440&&theme==='light') {
          await page.locator('#evidence').screenshot({path:'reports/pages_update_2026-09-05/evidence_desktop.png'});
          await page.locator('#experiment').screenshot({path:'reports/pages_update_2026-09-05/experiment_desktop.png'});
        }
        const row={file,theme,width,scrollWidth:check.scrollWidth,brokenImages:check.images,localLinkFailures:failures,scriptErrors:[...errors]};
        results.push(row);
      }
      await page.close();
    }
  }
  await browser.close();
  fs.writeFileSync('reports/pages_update_2026-09-05/browser_checks.json',JSON.stringify(results,null,2)+'\n');
  console.log(JSON.stringify(results));
  if(results.some(r=>r.scrollWidth>r.width||r.brokenImages.length||r.localLinkFailures.length||r.scriptErrors.length))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
