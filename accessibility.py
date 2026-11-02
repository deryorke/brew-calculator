# Accessibility regression tests (what the audit found and fixed)
from playwright.sync_api import sync_playwright
import sys
URL=sys.argv[1]; res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
CONTRAST=r'''()=>{
const parse=c=>{const m=c.match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}};
const lin=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};
const L=c=>0.2126*lin(c.r)+0.7152*lin(c.g)+0.0722*lin(c.b);
const over=(f,b)=>({r:f.r*f.a+b.r*(1-f.a),g:f.g*f.a+b.g*(1-f.a),b:f.b*f.a+b.b*(1-f.a),a:1});
const bgOf=el=>{let layers=[],unknown=false;for(let e=el;e;e=e.parentElement){const cs=getComputedStyle(e);if(cs.backgroundImage&&cs.backgroundImage!=='none'){unknown=true;break}const c=parse(cs.backgroundColor);if(c&&c.a>0){layers.push(c);if(c.a>=1)break}}
  let base={r:255,g:255,b:255,a:1};for(let i=layers.length-1;i>=0;i--)base=over(layers[i],base);return {c:base,unknown}};
const out=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(w.nextNode()){const n=w.currentNode,e=n.parentElement;if(!e||['SCRIPT','STYLE'].includes(e.tagName)||e.closest('[aria-hidden=true]'))continue;const t=n.nodeValue.trim();if(!t)continue;
  let hid=false;for(let x=e;x;x=x.parentElement){const cs=getComputedStyle(x);if(x.hidden||cs.display==='none'||cs.visibility==='hidden'){hid=true;break}}if(hid)continue;
  const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;
  const cs=getComputedStyle(e),fg=parse(cs.color);if(!fg)continue;const {c:bg,unknown}=bgOf(e);if(unknown)continue;
  const f=fg.a<1?over(fg,bg):fg;const l1=L(f),l2=L(bg),ratio=(Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
  const px=parseFloat(cs.fontSize),bold=parseInt(cs.fontWeight)>=700,large=px>=24||(px>=18.66&&bold);const need=large?3:4.5;
  if(ratio<need)out.push({text:t.slice(0,28),ratio:+ratio.toFixed(2),need,px:Math.round(px),sel:(e.tagName+'.'+(e.className||'')).slice(0,34),dis:e.disabled||!!e.closest('[disabled]')});}
return out;}'''
FOCUS=r"""()=>{const el=document.activeElement;if(!el||el===document.body)return null;const cs=getComputedStyle(el);return {t:el.tagName+'#'+el.id,ring:(cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>0)||cs.boxShadow!=='none'}}"""
VIEWS=[('home',"navigate('home')"),('calculator',"navigate('calculator')"),('recipes',"navigate('recipes')"),('timer',"navigate('timer')"),('settings',"navigate('settings')"),('detail',"openDetail('v60-classic')"),('form',"openRecipeForm('new')")]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(300); pg.evaluate("toggleFavorite('v60-classic');selectRecipeForBrewing('v60-classic')")
    titles={}
    for name,setup in VIEWS:
        pg.evaluate(setup); pg.wait_for_timeout(150)
        h1=pg.evaluate("[...document.querySelectorAll('h1')].filter(h=>h.offsetParent).length"); ck(f'{name}: exactly one visible h1',h1==1,h1)
        titles[name]=pg.title(); small=pg.evaluate("""()=>[...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea')].filter(e=>{if(!e.offsetParent&&getComputedStyle(e).position!=='fixed')return false;const r=e.getBoundingClientRect();return r.width&&(r.width<44||r.height<44)&&!(e.type==='checkbox'&&e.closest('label'))&&!e.closest('.sr-only')&&!e.classList.contains('skip-link')}).map(e=>e.tagName+'#'+e.id+' '+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height))"""); ck(f'{name}: every control is at least 44x44 px',not small,small[:3])
    ck('document title differs per view and names the app',len(set(titles.values()))>=6 and all('Brew Calculator' in t for t in titles.values()),titles)
    for th in ('light','dark'):
        pg.evaluate(f"()=>{{state.settings.theme='{th}';applySettings()}}"); pg.wait_for_timeout(500)   # let colour transitions finish before measuring
        bad=[]
        for name,setup in VIEWS: pg.evaluate(setup); pg.wait_for_timeout(100); bad+=[(name,x['text'],x['ratio']) for x in pg.evaluate(CONTRAST)]
        ck(f'text contrast meets WCAG AA in every view ({th}), decorative art excluded',not bad,bad[:3])
    pg.evaluate("()=>{state.settings.theme='light';applySettings()}")
    ck('decorative hero art is hidden from assistive tech',pg.evaluate("(navigate('home'),document.querySelector('.hero-art').getAttribute('aria-hidden'))")=='true')
    # skip link + landmarks
    pg.evaluate("navigate('settings')"); pg.evaluate("document.activeElement.blur()"); pg.keyboard.press('Tab'); ck('first Tab stop is the skip link',pg.evaluate("document.activeElement.id")=='skip-link' and pg.evaluate("document.activeElement.getBoundingClientRect().top>=0"),pg.evaluate("document.activeElement.id"))
    h=pg.evaluate("location.hash"); pg.keyboard.press('Enter'); pg.wait_for_timeout(100); ck('skip link moves focus to the content without changing the route',pg.evaluate("document.activeElement.id")=='app' and pg.evaluate("location.hash")==h and pg.is_visible('#view-settings'))
    # focus rings on every stop
    miss=[]
    for name,setup in VIEWS[:5]:
        pg.evaluate(setup); pg.wait_for_timeout(120); pg.evaluate("document.activeElement.blur()")
        for i in range(70):
            pg.keyboard.press('Tab'); f=pg.evaluate(FOCUS)
            if not f: break
            if not f['ring']: miss.append((name,f['t']))
    ck('every keyboard stop shows a focus indicator',not miss,miss[:3])
    # announcements
    pg.evaluate("navigate('home')"); pg.wait_for_timeout(100); pg.evaluate("navigate('recipes')"); pg.wait_for_timeout(250)
    ck('changing view is announced',pg.inner_text('#announcer').strip()=='Recipes',repr(pg.inner_text('#announcer')))
    pg.evaluate("navigate('timer')"); pg.click('#btn-start'); pg.wait_for_timeout(300); pg.click('#btn-skip'); pg.wait_for_timeout(300)
    t=pg.inner_text('#announcer'); ck('a new brewing step is announced with its instruction',len(t)>15 and t!='Timer',repr(t))
    # progress semantics
    pg.wait_for_timeout(1300); a=pg.evaluate("[document.getElementById('step-progress-track'),document.getElementById('overall-progress-track')].map(e=>[e.getAttribute('role'),e.getAttribute('aria-label'),e.getAttribute('aria-valuenow')])")
    ck('both progress bars expose role, name and value',all(x[0]=='progressbar' and x[1] and x[2] is not None for x in a),a); ck('overall progress value increases while brewing',int(a[1][2])>0,a)
    pg.evaluate("()=>{state.settings.language='id';applySettings()}"); lb=pg.evaluate("document.getElementById('overall-progress-track').getAttribute('aria-label')"); ck('progress names and skip link are translated',lb=='Progres keseluruhan' and 'Lewati' in pg.inner_text('#skip-link'),lb)
    pg.evaluate("()=>{state.settings.language='en';applySettings()}")
    # form errors
    pg.evaluate("navigate('timer');openRecipeForm('new')"); pg.wait_for_timeout(150); pg.fill('#f-dose','-5'); pg.fill('#f-ratio','0'); pg.click('#btn-save-recipe'); pg.wait_for_timeout(250)
    inv=pg.evaluate("[...document.querySelectorAll('#view-recipe-form [aria-invalid=true]')].map(e=>[e.id,e.getAttribute('aria-describedby')])")
    ck('every invalid field is marked and linked to the error summary',len(inv)>=3 and all(x[1]=='form-errors' for x in inv),inv)
    ck('focus moves to the first invalid field',pg.evaluate("document.activeElement.id")==inv[0][0],pg.evaluate("document.activeElement.id"))
    pg.fill('#f-name','Fixed'); pg.click('#btn-save-recipe'); pg.wait_for_timeout(250); ck('marks are cleared once errors change',pg.evaluate("document.querySelectorAll('#f-name[aria-invalid]').length")==0)
    # dialog
    pg.evaluate("()=>{const r=normalizeRecipe({...getRecipe('v60-classic')});r.id='ux';r.builtIn=false;r.name='Mine';state.userRecipes.push(r);rebuildRecipes();openDetail('ux')}"); pg.wait_for_timeout(150)
    pg.focus('#recipe-detail [data-action=delete]'); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ck('confirm dialog is modal, focused, closes on Esc and returns focus',pg.evaluate("document.getElementById('confirm-dialog').matches(':modal')") and pg.evaluate("document.activeElement.closest('dialog')!==null"),'')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200); ck('focus returns to the delete button after Esc',pg.evaluate("document.activeElement.dataset.action")=='delete')
    # reflow
    pg2=b.new_page(viewport={'width':320,'height':640}); pg2.goto(URL); pg2.wait_for_timeout(300); pg2.evaluate("selectRecipeForBrewing('v60-classic')"); ov=[]
    for fs in ('150%','200%'):
        for v in ('home','calculator','recipes','timer','settings'):
            pg2.evaluate(f"navigate('{v}')"); pg2.evaluate(f"document.documentElement.style.fontSize='{fs}'"); pg2.wait_for_timeout(100)
            if pg2.evaluate("document.documentElement.scrollWidth>innerWidth+1"): ov.append((fs,v))
    ck('no horizontal scrolling at 320 px with 150% and 200% text',not ov,ov)
    ck('no console errors',not errs,errs[:2]); b.close()
f=[r for r in res if not r[1]]; print(f'ACCESSIBILITY: {len(res)-len(f)}/{len(res)} passed')
for n,_,d in f: print('  FAIL',n,'|',d[:260])
sys.exit(1 if f else 0)
