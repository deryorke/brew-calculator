from playwright.sync_api import sync_playwright
import json, os, sys, tempfile
TMP=tempfile.mkdtemp(prefix='brew-test-')
U=sys.argv[1]
res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(accept_downloads=True); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.add_init_script("window.__persistCalls=0;window.__persistAnswer=false;if(navigator.storage){navigator.storage.persist=async()=>{window.__persistCalls++;window.__persisted=window.__persistAnswer;return window.__persistAnswer};navigator.storage.persisted=async()=>!!window.__persisted;}")
    pg.goto(U); pg.wait_for_timeout(400)
    vis=lambda s: pg.is_visible(s)
    pg.evaluate("navigate('recipes')"); ck('no recipes -> no backup nudge',not vis('#backup-nudge'))
    pg.evaluate("navigate('settings')"); pg.wait_for_timeout(200)
    ck('settings shows "Last backup: never."','never' in pg.inner_text('#backup-status'),pg.inner_text('#backup-status'))
    ck('settings shows current storage status without asking',vis('#persist-status') and 'not protected' in pg.inner_text('#persist-status') and pg.evaluate("__persistCalls")==0,pg.inner_text('#persist-status'))
    # add a recipe through the real form-save path -> persist requested, nudge appears
    pg.evaluate("__persistAnswer=true")
    pg.evaluate("()=>{openRecipeForm('copy','v60-classic')}"); pg.wait_for_timeout(150); pg.click('#btn-save-recipe'); pg.wait_for_timeout(400)
    ck('saving a recipe asks the browser for persistent storage',pg.evaluate("__persistCalls")>=1,pg.evaluate("__persistCalls"))
    pg.evaluate("navigate('recipes')"); pg.wait_for_timeout(150)
    ck('own recipe + no backup -> nudge visible with count',vis('#backup-nudge') and '1' in pg.inner_text('#backup-nudge-text'),pg.inner_text('#backup-nudge-text'))
    pg.evaluate("navigate('settings')"); pg.wait_for_timeout(150); ck('storage now reported as protected','protected:' in pg.inner_text('#persist-status') and 'not protected' not in pg.inner_text('#persist-status'),pg.inner_text('#persist-status'))
    # snooze
    pg.evaluate("navigate('recipes')"); pg.click('#btn-nudge-later'); pg.wait_for_timeout(150); ck('"Remind me later" hides the nudge',not vis('#backup-nudge'))
    pg.reload(); pg.wait_for_timeout(400); pg.evaluate("navigate('recipes')"); ck('snooze survives reload',not vis('#backup-nudge'))
    pg.evaluate("()=>{const m=JSON.parse(localStorage.getItem('brewCalculator.meta.v1'));m.snoozedAt=Date.now()-15*86400000;localStorage.setItem('brewCalculator.meta.v1',JSON.stringify(m))}"); pg.evaluate("navigate('settings');navigate('recipes')"); ck('nudge returns after the 14-day snooze',vis('#backup-nudge'))
    # export from the nudge
    with pg.expect_download() as d: pg.click('#btn-nudge-export')
    pg.wait_for_timeout(300); ck('export from nudge downloads a file',d.value.suggested_filename.endswith('.json'))
    ck('after export the nudge is gone',not vis('#backup-nudge'))
    pg.evaluate("navigate('settings')"); pg.wait_for_timeout(150); ck('last backup date is shown',any(c.isdigit() for c in pg.inner_text('#backup-status')) and 'never' not in pg.inner_text('#backup-status'),pg.inner_text('#backup-status'))
    # 31 days later it asks again
    pg.evaluate("()=>{const m=JSON.parse(localStorage.getItem('brewCalculator.meta.v1'));m.lastBackup=Date.now()-31*86400000;localStorage.setItem('brewCalculator.meta.v1',JSON.stringify(m))}"); pg.evaluate("navigate('recipes')"); ck('nudge returns 31 days after last backup',vis('#backup-nudge'))
    # import also requests persistence
    n0=pg.evaluate("__persistCalls"); json.dump({'app':'brew-calculator','version':2,'userRecipes':[{**pg.evaluate("JSON.parse(JSON.stringify(state.userRecipes[0]))"),'id':'zz','name':'Imported'}]},open(os.path.join(TMP,'imp.json'),'w')); pg.evaluate("navigate('settings')"); pg.set_input_files('#import-file',os.path.join(TMP,'imp.json')); pg.wait_for_timeout(400)
    ck('import also asks for persistent storage',pg.evaluate("__persistCalls")>n0)
    # robustness
    for bad in ['{oops','[]','"x"','null','{"lastBackup":"soon","snoozedAt":{}}']:
        pg.evaluate("v=>localStorage.setItem('brewCalculator.meta.v1',v)",bad); pg.reload(); pg.wait_for_timeout(300); pg.evaluate("navigate('recipes');navigate('settings')")
        ck(f'bad meta {bad[:18]} tolerated',pg.is_visible('#view-settings') and pg.inner_text('#backup-status')!='')
    # Indonesian
    pg.evaluate("()=>{state.settings.language='id';applySettings()}"); pg.evaluate("navigate('recipes')"); t=pg.inner_text('#backup-nudge'); pg.evaluate("navigate('settings')"); t2=pg.inner_text('#backup-status')+' '+pg.inner_text('#persist-status')
    ck('Indonesian nudge and status',('Kamu punya' in t and 'Ekspor sekarang' in t) and ('Cadangan terakhir' in t2),(t[:80],t2[:120]))
    # language switch on settings page refreshes the status text immediately
    pg.evaluate("()=>{state.settings.language='en';applySettings()}"); ck('switching language updates the status line at once','Last backup' in pg.inner_text('#backup-status'),pg.inner_text('#backup-status'))
    # storage API missing
    ck('no console errors',not errs,errs[:2]); b.close()
    pg=None
f=[r for r in res if not r[1]]; print(f'DATA-SAFETY: {len(res)-len(f)}/{len(res)} passed')
for n,_,d in f: print('  FAIL',n,'|',d[:200])
sys.exit(1 if f else 0)
