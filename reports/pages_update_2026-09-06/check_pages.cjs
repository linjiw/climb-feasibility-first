const { chromium } = require('/tmp/climb-pages-review/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-gpu']});
  const results=[];
  const base='http://127.0.0.1:8768/';
  for (const theme of ['light','dark']) for (const width of [390,1440]) {
    const page=await browser.newPage({viewport:{width,height:1000},colorScheme:theme,deviceScaleFactor:1});
    for (const file of ['index.html','relative-progress.html','archive-2026-09-05.html','flagship.html','companion.html','segment-native.html']) {
      const errors=[];
      const onError=e=>errors.push(e.message);
      page.on('pageerror',onError);
      await page.goto(base+file,{waitUntil:'networkidle'});
      const state=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,h1:document.querySelector('h1')?.textContent,images:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src),links:[...document.querySelectorAll('a[href],link[rel=stylesheet],img[src],script[src]')].map(e=>e.getAttribute('href')||e.getAttribute('src'))}));
      const failures=[];
      for (const link of state.links) {
        if(!link||/^(https?:|mailto:|data:)/.test(link))continue;
        const url=new URL(link,base+file);
        const local=path.join(process.cwd(),'docs',decodeURIComponent(url.pathname));
        if(!fs.existsSync(local))failures.push('Missing file: '+link);
        else if(url.hash&&local.endsWith('.html')){
          const text=fs.readFileSync(local,'utf8');
          if(!text.includes('id="'+url.hash.slice(1)+'"')&&!text.includes("id='"+url.hash.slice(1)+"'"))failures.push('Missing anchor: '+link);
        }
      }
      if(file==='index.html'){
        assert.equal(await page.locator('.question-picker').isVisible(),true);
        await page.getByRole('button',{name:'Estimator noise',exact:true}).click();
        assert.equal(await page.locator('#mechanism-detail h3').innerText(),'Estimator noise');
        assert.equal(await page.getByRole('button',{name:'Estimator noise',exact:true}).getAttribute('aria-pressed'),'true');
        await page.getByRole('button',{name:'Persistent difficulty',exact:true}).focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#mechanism-detail h3').innerText(),'Persistent difficulty');
        await page.getByRole('button',{name:'Recoverable decline',exact:true}).click();
        await page.evaluate(()=>scrollTo(0,0));
      }
      if(['index.html','relative-progress.html'].includes(file)){
        await page.screenshot({path:`reports/pages_update_2026-09-06/${file.replace('.html','')}_${width}_${theme}.png`});
        if(width===1440&&theme==='light')await page.locator(file==='index.html'?'#roadmap':'#evidence').screenshot({path:`reports/pages_update_2026-09-06/${file.replace('.html','')}_evidence.png`});
      }
      results.push({file,theme,width,scrollWidth:state.scrollWidth,brokenImages:state.images,localLinkFailures:failures,scriptErrors:errors});
      page.off('pageerror',onError);
    }
    await page.close();
  }
  const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});
  await nojs.goto(base);
  assert.equal(await nojs.locator('.question-picker').isVisible(),false);
  assert.equal(await nojs.locator('noscript').isVisible(),true);
  assert.match(await nojs.locator('body').innerText(),/10 \/ 12/);
  await browser.close();
  fs.writeFileSync('reports/pages_update_2026-09-06/browser_checks.json',JSON.stringify({checks:results,keyboard_interaction:'pass',no_javascript_fallback:'pass'},null,2)+'\n');
  const bad=results.filter(r=>r.scrollWidth>r.width||r.brokenImages.length||r.localLinkFailures.length||r.scriptErrors.length);
  console.log(JSON.stringify({views:results.length,failures:bad},null,2));
  if(bad.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
