# Part 3: storage failures, corrupt data, offline, update flow
from playwright.sync_api import sync_playwright
import sys,json,shutil,os,re
import _common
SRC=sys.argv[1]; res=[]
last=['start']
def ck(n,c,d=''): last[0]=n; res.append((n,bool(c),str(d)))
SITE=_common.copy_site(SRC)
BASE,_stop=_common.start(SITE)
class srv:   # keeps the old terminate() calls working
    terminate=staticmethod(_stop)

def _hook(t,v,tb):
    print('CRASH after check:',last[0],'|',str(v)[:260].replace(chr(10),' ')); 
    srv.terminate()
    fails=[r for r in res if not r[1]]; print(f'partial: {len(res)-len(fails)}/{len(res)} passed')
    for n,_,d in fails: print('  FAIL',n,'|',d[:200])
sys.excepthook=_hook
U=BASE+'index.html'
KEYS=['brewCalculator.v2','brewCalculator.brew.v1']
with sync_playwright() as p:
    b=p.chromium.launch()
    # 1. corrupt / hostile stored data must never break startup
    junk=['{oops','[]','"x"','null','123','{"version":99,"settings":{"language":"fr","theme":5,"units":{}},"userRecipes":"x","favorites":7}',
          '{"version":2,"userRecipes":[{"name":"<img src=x onerror=window.__x=1>","method":"Espresso","dose":-1}],"favorites":["a"],"recent":[null]}','{"version":2,"lastRecipeId":{"a":1},"settings":null}',
          json.dumps({'version':2,'userRecipes':[{'name':'n'+str(i)} for i in range(3000)]}), '{"version":1,"recipes":[1,2,3]}']
    for j in junk:
        for key in KEYS:
            ctx=b.new_context(); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            pg.add_init_script(f"try{{localStorage.setItem({json.dumps(key)},{json.dumps(j)})}}catch(e){{}}")
            pg.goto(U); pg.wait_for_timeout(300)
            ok=pg.evaluate("typeof state!=='undefined'&&state.recipes.length>=6&&!!document.querySelector('#view-home')&&!document.getElementById('view-home').hidden")
            ck(f'startup survives {key.split(".")[-1]} = {j[:34]}',ok and not errs and pg.evaluate("window.__x")is None,errs[:1])
            ctx.close()
    # 2. storage completely unavailable / full
    for mode,js in [('setItem throws (quota)',"Storage.prototype.setItem=function(){throw new DOMException('full','QuotaExceededError')}"),
                    ('localStorage blocked',"Object.defineProperty(window,'localStorage',{get(){throw new DOMException('denied','SecurityError')}})")]:
        ctx=b.new_context(); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.add_init_script(js)
        pg.goto(U); pg.wait_for_timeout(400)
        ck(f'app starts when {mode}',pg.evaluate("typeof state!=='undefined'&&state.recipes.length>=6") and not errs,errs[:1])
        pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start'); pg.wait_for_timeout(1300)
        ck(f'timer works when {mode}',pg.evaluate("state.engine.status")=='running' and not errs,errs[:1])
        try:
            pg.evaluate("navigate('calculator')"); pg.fill('#calc-dose','21'); pg.dispatch_event('#calc-dose','input'); pg.wait_for_timeout(150); ck(f'calculator works when {mode}',pg.input_value('#calc-water')!='' and not errs,errs[:1])
            pg.evaluate("toggleFavorite('v60-classic')"); pg.evaluate("state.settings.sound=false;saveState()"); pg.wait_for_timeout(200)
            ck(f'saving does not crash when {mode}',not errs,errs[:1]); 
            ck(f'user is told saving does not work when {mode}','not letting the app save' in pg.evaluate("document.getElementById('toast').textContent"),pg.evaluate("document.getElementById('toast').textContent"))
        except Exception as e: ck(f'interaction when {mode}',False,str(e)[:150])
        ctx.close()
    # 3. offline behaviour on every route + after browser restart
    ctx=b.new_context(); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(U); pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(500)
    ck('service worker controls the page',pg.evaluate("!!navigator.serviceWorker.controller"))
    pg.evaluate("()=>{const r=normalizeRecipe({...getRecipe('v60-classic'),name:'Offline Recipe'});r.id='u-off';r.builtIn=false;state.userRecipes.push(r);rebuildRecipes();saveState();}")
    ctx.set_offline(True)
    for route in ['home','calculator','recipes','timer','settings']:
        pg.goto(U+'#'+route); pg.wait_for_timeout(350)
        ck(f'offline reload #{route} renders',pg.is_visible(f'#view-{route}') and pg.evaluate("state.userRecipes.some(r=>r.name==='Offline Recipe')"))
    pg.goto(U+'?utm=1#home'); pg.wait_for_timeout(300); ck('offline with query string still loads',pg.is_visible('#view-home'))
    pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start'); pg.wait_for_timeout(1500); ck('offline timer runs',pg.evaluate("state.engine.status")=='running')
    for f in ['manifest.webmanifest','icons/icon-192.png','icons/icon-512.png','icons/maskable-512.png','icons/apple-touch-icon.png','sw.js']:
        st=pg.evaluate("u=>fetch(u).then(r=>r.status).catch(()=>0)",f); ck(f'offline asset {f}',st==200,st)
    ctx.set_offline(False)
    # 4. timer survives restarts: running, paused, manual mode, long gaps
    pg.evaluate("navigate('timer')"); pg.click('#btn-reset'); pg.wait_for_timeout(150)
    pg.evaluate("()=>{state.settings.autoAdvance=true;saveState()}"); pg.evaluate("selectRecipeForBrewing('v60-classic')"); pg.click('#btn-start'); pg.wait_for_timeout(1500)
    pg.reload(); pg.wait_for_timeout(600); ck('running brew restored after reload',pg.evaluate("state.engine.status")=='running' and pg.evaluate("state.lastSnap.overallMs")>=1400)
    pg.evaluate("navigate('timer')"); pg.click('#btn-pause'); pg.wait_for_timeout(200); ov=pg.evaluate("state.engine.baseMs"); pg.reload(); pg.wait_for_timeout(500)
    ck('paused brew restored with same elapsed',pg.evaluate("state.engine.status")=='paused' and abs(pg.evaluate("state.engine.baseMs")-ov)<5)
    pg.evaluate("navigate('timer')"); pg.click('#btn-reset')
    pg.evaluate("()=>{state.settings.autoAdvance=false;saveState()}"); pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start')
    pg.evaluate("()=>{const k='brewCalculator.brew.v1',o=JSON.parse(localStorage.getItem(k));o.eng.startedAt-=3600000;localStorage.setItem(k,JSON.stringify(o))}"); pg.reload(); pg.wait_for_timeout(600)
    ck('manual mode: 1h gap does NOT skip steps (waits at step end)',pg.evaluate("state.engine.status")=='running' and pg.evaluate("state.engine.index")==0 and pg.evaluate("state.engine.waiting")==True,pg.evaluate("[state.engine.status,state.engine.index,state.engine.waiting]"))
    pg.evaluate("navigate('timer')"); pg.click('#btn-skip'); pg.wait_for_timeout(200); ck('manual mode: Next advances after the wait',pg.evaluate("state.engine.index")==1)
    pg.evaluate("()=>{state.settings.autoAdvance=true;saveState()}")
    # 5. update flow
    import re as _re; sw=_re.sub(r"CACHE_VERSION = '[^']+'","CACHE_VERSION = 'v99'",open(SITE+'/sw.js').read()); open(SITE+'/sw.js','w').write(sw)
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.update())"); pg.wait_for_timeout(1500)
    ck('new SW version offers an update banner',not pg.evaluate("document.getElementById('update-banner').hidden"))
    ck('page keeps running old version until accepted',pg.evaluate("!!navigator.serviceWorker.controller")) 
    st=pg.evaluate("state.engine.status")
    with pg.expect_navigation(timeout=8000): pg.click('#btn-update')
    pg.wait_for_timeout(1000); ck('after update only the new cache remains',pg.evaluate("caches.keys()")==['brew-calculator-v99'],pg.evaluate("caches.keys()"))
    ck('running brew survives the update reload',pg.evaluate("state.engine.status")==st,(st,pg.evaluate("state.engine.status")))
    ck('no page errors in offline/restore/update flows',not errs,errs[:2])
    b.close()

srv.terminate()
fails=[r for r in res if not r[1]]
print(f'RESILIENCE/PWA: {len(res)-len(fails)}/{len(res)} passed')
for n,_,d in fails: print('  FAIL',n,'|',d[:260])
sys.exit(1 if fails else 0)
