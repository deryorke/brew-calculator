# Part 2: end-to-end UI behaviour with real clicks and typing
from playwright.sync_api import sync_playwright
import sys,json,re,os,tempfile
TMP=tempfile.mkdtemp(prefix='brew-test-')
URL=sys.argv[1]
res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
def body_text(pg): return pg.evaluate("document.body.innerText")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(accept_downloads=True,viewport={'width':420,'height':900}); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append('pageerror '+str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(400)
    vis=lambda sel: pg.is_visible(sel)
    # --- navigation
    ck('home visible on first load',vis('#view-home'))
    for label,view in [('Calculator','calculator'),('Recipes','recipes'),('Timer','timer'),('Settings','settings'),('Home','home')]:
        pg.click(f'.nav button:has-text("{label}")'); pg.wait_for_timeout(120); ck(f'nav click -> {view}',vis(f'#view-{view}') and pg.evaluate("location.hash")=='#'+view,pg.evaluate("location.hash"))
    pg.evaluate("location.hash='#settings'"); pg.wait_for_timeout(150); ck('hash change navigates (deep links)',vis('#view-settings'))
    pg.evaluate("navigate('home')")
    # --- theme
    t0=pg.evaluate("document.documentElement.dataset.theme"); pg.click('#theme-quick'); t1=pg.evaluate("document.documentElement.dataset.theme"); ck('theme toggle flips',t0!=t1,(t0,t1))
    pg.reload(); pg.wait_for_timeout(300); ck('theme persists after reload',pg.evaluate("document.documentElement.dataset.theme")==t1)
    pg.click('#theme-quick')
    # --- calculator
    pg.evaluate("navigate('calculator')")
    pg.select_option('#calc-method','V60 / Pour Over'); pg.wait_for_timeout(100)
    opts=pg.evaluate("[...document.querySelectorAll('#calc-recipe option')].map(o=>o.value)"); ck('calc recipe list populated',len(opts)>=1,opts)
    pg.select_option('#calc-recipe','v60-classic'); pg.wait_for_timeout(100)
    pg.fill('#calc-dose','20'); pg.dispatch_event('#calc-dose','input'); pg.wait_for_timeout(100)
    ck('dose 20 x ratio 16 -> water 320',pg.input_value('#calc-water')=='320',pg.input_value('#calc-water'))
    pg.fill('#calc-water','300'); pg.dispatch_event('#calc-water','input'); pg.wait_for_timeout(100)
    d=float(pg.input_value('#calc-dose')); r=float(pg.input_value('#calc-ratio')); ck('water 300 -> dose consistent',abs(d*r-300)<0.2,(d,r))
    pg.fill('#calc-ratio','15'); pg.dispatch_event('#calc-ratio','input'); pg.wait_for_timeout(100)
    d=float(pg.input_value('#calc-dose')); w=float(pg.input_value('#calc-water')); ck('ratio change keeps dose, recomputes water',abs(d*15-w)<0.1,(d,w))
    pg.fill('#calc-dose',''); pg.dispatch_event('#calc-dose','input'); pg.wait_for_timeout(100); ck('empty dose shows error',vis('#calc-error') and len(pg.inner_text('#calc-error'))>3,pg.inner_text('#calc-error'))
    ck('error blocks the result card',not pg.is_visible('#btn-calc-to-brew') or pg.is_disabled('#btn-calc-to-brew'))
    pg.fill('#calc-dose','18'); pg.dispatch_event('#calc-dose','input'); pg.wait_for_timeout(100); ck('error clears after valid input',not vis('#calc-error'))
    w=float(pg.input_value('#calc-water'))
    pg.click('#btn-calc-to-brew'); pg.wait_for_timeout(300); ck('calc -> brew opens timer',vis('#view-timer'))
    steps=pg.evaluate("state.activeBrew.steps.map(s=>s.targetWater)"); ck('timer steps scaled: last target = water',abs(steps[-1]-w)<0.01 and all(steps[i]>=steps[i-1] for i in range(1,len(steps))),(steps,w))
    ck('built-in V60 untouched after scaling',pg.evaluate("getRecipe('v60-classic').water")==240)
    # --- timer realtime
    pg.click('#btn-start'); pg.wait_for_timeout(2300); t=pg.inner_text('#timer-overall-text'); ck('timer advances in real time',re.search(r'00:0[1-3]',t) is not None,t)
    pg.click('#btn-pause'); pg.wait_for_timeout(200); a=pg.inner_text('#timer-display'); pg.wait_for_timeout(1500); b2=pg.inner_text('#timer-display'); ck('pause freezes display',a==b2,(a,b2)); ck('resume button shown while paused',vis('#btn-resume'))
    pg.click('#btn-resume'); pg.wait_for_timeout(1300); c=pg.inner_text('#timer-display'); ck('resume continues',c!=b2,(b2,c))
    i0=pg.evaluate("state.engine.index"); pg.click('#btn-skip'); pg.wait_for_timeout(200); ck('skip moves to next step',pg.evaluate("state.engine.index")==i0+1)
    pg.click('#btn-reset'); pg.wait_for_timeout(200); ck('reset returns to idle',pg.evaluate("state.engine.status")=='idle' and vis('#btn-start'))
    pg.click('#btn-start'); pg.wait_for_timeout(200)
    for _ in range(12):
        if pg.evaluate("state.engine.status")=='complete': break
        pg.click('#btn-skip'); pg.wait_for_timeout(80)
    pg.wait_for_timeout(250); ck('finishing shows completion card',vis('#timer-complete') and len(pg.inner_text('#complete-summary'))>5,pg.evaluate("state.engine.status"))
    pg.click('#btn-brew-again'); pg.wait_for_timeout(200); ck('brew again resets to idle',pg.evaluate("state.engine.status")=='idle')
    # --- create / edit / favorite / duplicate / delete recipes
    pg.evaluate("navigate('recipes')"); pg.click('#btn-create-recipe'); pg.wait_for_timeout(200); ck('create form opens',vis('#view-recipe-form'))
    pg.click('#btn-save-recipe'); pg.wait_for_timeout(200); ck('empty form shows validation errors',vis('#form-errors') and pg.inner_text('#form-errors').count('\n')>=1,pg.inner_text('#form-errors')[:80])
    pg.fill('#f-name','Test Brew ☕'); pg.select_option('#f-method','V60 / Pour Over'); pg.fill('#f-dose','20'); pg.fill('#f-water','320'); pg.fill('#f-ratio','16'); pg.fill('#f-temp','93'); pg.fill('#f-estimate','2:30')
    while pg.locator('#f-steps [data-key="name"]').count()<2: pg.click('#btn-add-step')
    st=[('Bloom','30','60','Pour {target}'),('Main','60','320','Spiral to {target}')]
    for i,(n,du,tg,ins) in enumerate(st):
        for k,v in zip(['name','duration','target','instruction'],[n,du,tg,ins]): pg.fill(f'#f-steps [data-step="{i}"][data-key="{k}"]',v)
    pg.click('#btn-save-recipe'); pg.wait_for_timeout(300)
    ur=pg.evaluate("state.userRecipes"); ck('recipe saved',len(ur)==1 and ur[0]['name']=='Test Brew ☕' and ur[0]['water']==320 and not ur[0].get('builtIn'),json.dumps(ur)[:200]); rid=ur[0]['id'] if ur else None
    landed=pg.evaluate("[...document.querySelectorAll('section[id^=view-]')].filter(e=>!e.hidden&&e.offsetParent).map(e=>e.id)"); ck('after save the app leaves the form',landed!=['view-recipe-form'] and len(landed)==1,landed)
    pg.evaluate("navigate('recipes')"); pg.wait_for_timeout(150); ck('saved recipe appears in list','Test Brew' in pg.inner_text('#recipe-list'))
    pg.fill('#recipe-search','test brew'); pg.wait_for_timeout(200); ck('search finds it',pg.locator('#recipe-list [data-action=open]').count()==1)
    pg.fill('#recipe-search','zzzz'); pg.wait_for_timeout(200); ck('no match shows empty state',pg.locator('#recipe-list [data-action=open]').count()==0 and 'Clear' in pg.inner_text('#recipe-list'))
    pg.click('#recipe-list [data-action=clear-filters]'); pg.wait_for_timeout(200); ck('clear filters restores list',pg.locator('#recipe-list [data-action=open]').count()>=7)
    pg.fill('#recipe-search','test brew'); pg.wait_for_timeout(150); pg.click('#recipe-list [data-action=favorite]'); pg.wait_for_timeout(150); ck('favorite toggles on',rid in pg.evaluate("state.favorites"))
    pg.fill('#recipe-search',''); 
    pg.evaluate(f"openDetail('{rid}')"); pg.wait_for_timeout(200)
    pg.click('#recipe-detail [data-action=edit]'); pg.wait_for_timeout(200); pg.fill('#f-name','Test Brew v2'); pg.click('#btn-save-recipe'); pg.wait_for_timeout(300)
    ck('edit saves in place (same id, new name)',pg.evaluate("state.userRecipes.length")==1 and pg.evaluate("state.userRecipes[0].name")=='Test Brew v2' and pg.evaluate("state.userRecipes[0].id")==rid)
    pg.evaluate("openDetail('v60-classic')"); pg.wait_for_timeout(150); pg.click('#recipe-detail [data-action=edit]'); pg.wait_for_timeout(200); pg.click('#btn-save-recipe'); pg.wait_for_timeout(300)
    ck('"Edit as my copy" of built-in creates a copy, built-in intact',pg.evaluate("state.userRecipes.length")==2 and pg.evaluate("getRecipe('v60-classic').builtIn")==True and pg.evaluate("getRecipe('v60-classic').name")=='Classic V60')
    pg.evaluate(f"openDetail('{rid}')"); pg.wait_for_timeout(150); pg.click('#recipe-detail [data-action=duplicate]'); pg.wait_for_timeout(250); ck('duplicate opens a prefilled copy form',vis('#view-recipe-form') and pg.input_value('#f-name').endswith('(copy)'),pg.input_value('#f-name')); pg.click('#btn-save-recipe'); pg.wait_for_timeout(300); n3=pg.evaluate("state.userRecipes.length"); ck('saving the copy adds a recipe',n3==3,n3)
    pg.reload(); pg.wait_for_timeout(400); ck('recipes + favorites persist after reload',pg.evaluate("state.userRecipes.length")==n3 and rid in pg.evaluate("state.favorites"))
    pg.evaluate(f"openDetail('{rid}')"); pg.wait_for_timeout(150); pg.click('#recipe-detail [data-action=delete]'); pg.wait_for_timeout(200); ck('delete asks for confirmation',pg.evaluate("document.getElementById('confirm-dialog').open"))
    pg.click('#confirm-cancel'); pg.wait_for_timeout(150); ck('cancel keeps the recipe',pg.evaluate("state.userRecipes.length")==n3)
    pg.click('#recipe-detail [data-action=delete]'); pg.wait_for_timeout(200); pg.click('#confirm-ok'); pg.wait_for_timeout(300); ck('confirm deletes it',pg.evaluate("state.userRecipes.length")==n3-1 and rid not in pg.evaluate("state.favorites"),pg.evaluate("state.favorites"))
    ck('built-in has no delete button',pg.evaluate("(openDetail('espresso-starter'),!document.querySelector('#recipe-detail [data-action=delete]'))"))
    # --- export / import round trip with awkward names
    pg.evaluate("""()=>{const r=normalizeRecipe({...getRecipe('espresso-starter')});r.id='u-edge1';r.builtIn=false;r.name='Ünï "quotes" <b>x</b> 日本 ☕';state.userRecipes.push(r);rebuildRecipes();saveState();}""")
    pg.evaluate("navigate('settings')")
    with pg.expect_download() as d: pg.click('#btn-export')
    path=os.path.join(TMP,'rt.json'); d.value.save_as(path); before=pg.evaluate("JSON.stringify(state.userRecipes.map(r=>r.name).sort())")
    pg.evaluate("()=>{state.userRecipes=[];rebuildRecipes();saveState();}"); pg.set_input_files('#import-file',path); pg.wait_for_timeout(300)
    ck('export -> wipe -> import restores every recipe',pg.evaluate("JSON.stringify(state.userRecipes.map(r=>r.name).sort())")==before,before[:120])
    pg.set_input_files('#import-file',path); pg.wait_for_timeout(300); ck('second import is idempotent',pg.evaluate("JSON.stringify(state.userRecipes.map(r=>r.name).sort())")==before)
    ck('markup in names stays text',pg.evaluate("(navigate('recipes'),document.querySelectorAll('#recipe-list b').length)")==0)
    # --- units
    pg.evaluate("navigate('settings')"); snap0=pg.evaluate("JSON.stringify(state.recipes.filter(r=>r.builtIn))")
    pg.select_option('#set-units','imperial'); pg.wait_for_timeout(200); pg.evaluate("navigate('calculator')"); pg.select_option('#calc-recipe','v60-classic'); pg.wait_for_timeout(150)
    ck('imperial shows oz in calculator',re.search(r'oz|°F',pg.inner_text('#view-calculator')) is not None)
    dv=float(pg.input_value('#calc-dose')); ck('dose shown in oz (~0.53)',0.4<dv<0.7,dv)
    for _ in range(3):
        pg.evaluate("navigate('settings')"); pg.select_option('#set-units','metric'); pg.wait_for_timeout(100); pg.select_option('#set-units','imperial'); pg.wait_for_timeout(100)
    pg.select_option('#set-units','metric'); pg.wait_for_timeout(150); ck('toggling units never alters stored recipes',pg.evaluate("JSON.stringify(state.recipes.filter(r=>r.builtIn))")==snap0)
    # imperial form save without edits keeps grams
    pg.select_option('#set-units','imperial'); pg.evaluate("openDetail('v60-classic')"); pg.click('#recipe-detail [data-action=edit]'); pg.wait_for_timeout(200); pg.click('#btn-save-recipe'); pg.wait_for_timeout(300)
    cp=pg.evaluate("state.userRecipes.find(r=>r.name.includes('Classic V60'))"); ck('imperial untouched save keeps exact grams/°C',cp and cp['dose']==15 and cp['water']==240 and cp['temp']==92,json.dumps(cp)[:160] if cp else 'none')
    pg.evaluate("navigate('settings')"); pg.select_option('#set-units','metric')
    # --- settings persistence
    pg.evaluate("navigate('settings')")
    for sel in ['#set-sound','#set-autoadvance','#set-wakelock']: pg.click(sel)
    pg.select_option('#set-timermode','up') if pg.evaluate("[...document.querySelectorAll('#set-timermode option')].some(o=>o.value==='up')") else None
    want=pg.evaluate("JSON.stringify(state.settings)"); pg.reload(); pg.wait_for_timeout(400); ck('all settings persist across reload',pg.evaluate("JSON.stringify(state.settings)")==want)
    # --- language round trip restores English exactly
    views=['home','calculator','recipes','timer','settings']
    def grab(): 
        out={}
        for v in views: pg.evaluate(f"navigate('{v}')"); pg.wait_for_timeout(80); out[v]=body_text(pg)
        return out
    en1=grab(); pg.evaluate("navigate('settings')"); pg.select_option('#set-language','id'); pg.wait_for_timeout(200); idt=grab(); pg.evaluate("navigate('settings')"); pg.select_option('#set-language','en'); pg.wait_for_timeout(200); en2=grab()
    ck('EN -> ID -> EN restores every view exactly',en1==en2,[v for v in views if en1[v]!=en2[v]])
    ck('ID differs from EN on every view',all(idt[v]!=en1[v] for v in views))
    ck('no leftover raw {placeholders} in any view',not any(re.search(r'\{\w+\}',t) for t in list(en1.values())+list(idt.values())))
    ck('no console errors during whole run',not errs,errs[:3])
    b.close()
fails=[r for r in res if not r[1]]
print(f'UI: {len(res)-len(fails)}/{len(res)} passed')
for n,_,d in fails: print('  FAIL',n,'|',d[:260])
sys.exit(1 if fails else 0)
