from playwright.sync_api import sync_playwright
import json, os, sys, tempfile
TMP=tempfile.mkdtemp(prefix='brew-test-')
U=sys.argv[1]; res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
def mk(pg,rid,name,extra=None):
    pg.evaluate("([rid,name])=>{const r=normalizeRecipe({...getRecipe('v60-classic')});r.id=rid;r.builtIn=false;r.name=name;state.userRecipes.push(r);rebuildRecipes();saveState();}",[rid,name])
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---- old phone: has recipes, favorites (built-in + own), custom settings
    c1=b.new_context(accept_downloads=True); a=c1.new_page(); errs=[]; a.on('pageerror',lambda e:errs.append(str(e))); a.on('console',lambda m:m.type=='error' and errs.append(m.text))
    a.goto(U); a.wait_for_timeout(300)
    mk(a,'u-own1','Morning V60 ☕'); mk(a,'u-own2','Evening <i>Press</i>')
    a.evaluate("()=>{toggleFavorite('v60-classic');toggleFavorite('u-own2');Object.assign(state.settings,{language:'id',units:'imperial',theme:'dark',timerMode:'up',autoAdvance:false,sound:false,vibrate:false,wakeLock:false,notify:true});saveState();applySettings();}")
    a.evaluate("navigate('settings')")
    with a.expect_download() as d: a.click('#btn-export')
    d.value.save_as(os.path.join(TMP,'full.json')); data=json.load(open(os.path.join(TMP,'full.json')))
    ck('export has recipes, favorites and settings',len(data['userRecipes'])==2 and set(data['favorites'])=={'v60-classic','u-own2'} and data['settings']['units']=='imperial',json.dumps(data)[:200])
    ck('export never includes the notification switch',data['settings'].get('notify') is None and 'recent' not in data)
    # ---- new phone
    c2=b.new_context(); n=c2.new_page(); e2=[]; n.on('pageerror',lambda e:e2.append(str(e))); n.on('console',lambda m:m.type=='error' and e2.append(m.text)); n.goto(U); n.wait_for_timeout(300); n.evaluate("navigate('settings')")
    n.set_input_files('#import-file',os.path.join(TMP,'full.json')); n.wait_for_timeout(300)
    ck('settings in file trigger a confirmation',n.evaluate("document.getElementById('confirm-dialog').open") and 'settings' in n.inner_text('#confirm-message').lower(),n.inner_text('#confirm-message')[:80])
    ck('recipes and favorites are imported before the settings question',n.evaluate("state.userRecipes.length")==2 and set(n.evaluate("state.favorites"))=={'v60-classic','u-own2'})
    ck('current settings unchanged while the question is open',n.evaluate("state.settings.units")=='metric' and n.evaluate("state.settings.language")=='en')
    n.click('#confirm-cancel'); n.wait_for_timeout(300)
    ck('cancel keeps current settings but keeps recipes+favorites',n.evaluate("state.settings.units")=='metric' and n.evaluate("state.userRecipes.length")==2 and 'favorite' in n.inner_text('#toast'),n.inner_text('#toast'))
    # new context 3: accept
    c3=b.new_context(); m=c3.new_page(); e3=[]; m.on('pageerror',lambda e:e3.append(str(e))); m.on('console',lambda x:x.type=='error' and e3.append(x.text)); m.goto(U); m.wait_for_timeout(300); m.evaluate("navigate('settings')")
    m.evaluate("()=>{state.settings.notify=false}")
    m.set_input_files('#import-file',os.path.join(TMP,'full.json')); m.wait_for_timeout(300); m.click('#confirm-ok'); m.wait_for_timeout(400)
    st=m.evaluate("state.settings"); ck('accepting applies every saved setting',st['language']=='id' and st['units']=='imperial' and st['theme']=='dark' and st['timerMode']=='up' and st['autoAdvance']==False and st['sound']==False and st['wakeLock']==False,json.dumps(st))
    ck('notification switch is NOT carried over',st['notify']==False)
    ck('UI reflects the new settings immediately',m.evaluate("document.documentElement.dataset.theme")=='dark' and m.evaluate("document.documentElement.lang")=='id' and m.evaluate("document.getElementById('set-units').value")=='imperial' and 'diterapkan' in m.inner_text('#toast'),m.inner_text('#toast'))
    m.reload(); m.wait_for_timeout(400); ck('imported settings, recipes, favorites persist after reload',m.evaluate("state.settings.units")=='imperial' and m.evaluate("state.userRecipes.length")==2 and 'u-own2' in m.evaluate("state.favorites"))
    m.evaluate("navigate('calculator')"); ck('imperial display active in calculator',any(t in m.inner_text('#view-calculator') for t in ['oz','°F']))
    # ---- id clash + identical-recipe mapping
    c4=b.new_context(); q=c4.new_page(); q.goto(U); q.wait_for_timeout(300)
    mk(q,'u-own1','Different recipe, same id'); 
    q.evaluate("()=>{const r=normalizeRecipe({...getRecipe('v60-classic')});r.id='u-zzz';r.builtIn=false;r.name='Evening <i>Press</i>';state.userRecipes.push(r);rebuildRecipes();saveState();}")  # identical content to u-own2 but another id
    q.evaluate("navigate('settings')"); q.set_input_files('#import-file',os.path.join(TMP,'full.json')); q.wait_for_timeout(300)
    if q.evaluate("document.getElementById('confirm-dialog').open"): q.click('#confirm-cancel'); q.wait_for_timeout(200)
    names=q.evaluate("state.userRecipes.map(r=>[r.id,r.name])"); ids=[x[0] for x in names]
    ck('clashing id gets a new id, nothing overwritten',len(ids)==len(set(ids)) and ['u-own1','Different recipe, same id'] in names and any(x[1]=='Morning V60 ☕' for x in names),names)
    fav=q.evaluate("state.favorites"); ck('favorite of an already-saved identical recipe points at the existing copy',('u-zzz' in fav) and ('u-own2' not in fav or q.evaluate("!!getRecipe('u-own2')")),fav)
    ck('no dangling favorites',all(q.evaluate("id=>!!getRecipe(id)",f) for f in fav),fav)
    # ---- other file shapes
    def imp(obj,answer=None):
        json.dump(obj,open(os.path.join(TMP,'x.json'),'w')); q.evaluate("navigate('settings')"); q.set_input_files('#import-file',os.path.join(TMP,'x.json')); q.wait_for_timeout(300)
        asked=q.evaluate("document.getElementById('confirm-dialog').open")
        if asked: q.click('#confirm-ok' if answer else '#confirm-cancel'); q.wait_for_timeout(250)
        return asked,q.inner_text('#toast')
    asked,t=imp({'app':'brew-calculator','version':2,'userRecipes':data['userRecipes']}); ck('old-format file (recipes only) imports with no settings question',not asked,t)
    cur=q.evaluate("JSON.parse(JSON.stringify(state.settings))"); asked,t=imp({'settings':{k:cur[k] for k in ['language','units','theme']}}); ck('settings identical to current -> no question, "nothing new"',not asked and 'Nothing new' in t or not asked,t)
    n0=len(q.evaluate("state.favorites")); asked,t=imp({'favorites':['espresso-starter','ghost',5,None,{},'__proto__']}); ck('favorites-only file: adds valid ids only',not asked and q.evaluate("state.favorites.includes('espresso-starter')") and not q.evaluate("state.favorites.some(f=>typeof f!=='string'||f==='ghost'||f==='__proto__')"),(t,q.evaluate("state.favorites")))
    asked,t=imp({'settings':{'language':'fr','units':{},'theme':7,'notify':True,'sound':'yes','__proto__':{'x':1}}},True); s2=q.evaluate("state.settings"); ck('hostile settings are ignored (invalid values, notify, proto)',s2['language'] in('en','id') and s2['units'] in('metric','imperial') and s2['theme'] in('light','dark') and s2['notify']==False and q.evaluate("({}).x")is None,json.dumps(s2))
    asked,t=imp({'favorites':[f'id{i}' for i in range(5000)]}); ck('huge favorites list does not hang or bloat',q.evaluate("state.favorites.length")<50,q.evaluate("state.favorites.length"))
    asked,t=imp({'a':1}); ck('unrelated JSON still rejected','does not contain' in t,t)
    asked,t=imp({'userRecipes':[]}); ck('empty recipe list message unchanged','No recipes found' in t,t)
    asked,t=imp({'userRecipes':[None,5,'x',[],{'name':'ok','steps':'x'}]}); ck('all-invalid recipes reported as skipped',asked is False and 'Skipped 5' in t,t)
    # idempotent second import
    q.evaluate("navigate('settings')"); n_before=q.evaluate("state.userRecipes.length"); q.set_input_files('#import-file',os.path.join(TMP,'full.json')); q.wait_for_timeout(300)
    if q.evaluate("document.getElementById('confirm-dialog').open"): q.click('#confirm-cancel'); q.wait_for_timeout(200)
    ck('importing the same backup twice adds nothing',q.evaluate("state.userRecipes.length")==n_before,(n_before,q.evaluate("state.userRecipes.length")))
    # export with no recipes still exports favorites/settings
    c5=b.new_context(accept_downloads=True); z=c5.new_page(); z.goto(U); z.wait_for_timeout(300); z.evaluate("toggleFavorite('espresso-starter');navigate('settings')")
    with z.expect_download() as d5: z.click('#btn-export')
    d5.value.save_as(os.path.join(TMP,'min.json')); md=json.load(open(os.path.join(TMP,'min.json'))); ck('export works with no own recipes (favorites + settings)',md['userRecipes']==[] and md['favorites']==['espresso-starter'] and 'language' in md['settings'] and 'favorites' in z.inner_text('#toast').lower(),z.inner_text('#toast'))
    ck('Indonesian dialog texts exist',m.evaluate("[T('Apply the saved settings?'),T('Apply'),T('Settings applied.'),T('{n} favorite(s) restored.',{n:2})]").count('Apply')==0)
    ck('no console errors anywhere',not (errs or e2 or e3),(errs+e2+e3)[:2]); b.close()
f=[r for r in res if not r[1]]; print(f'FULL BACKUP: {len(res)-len(f)}/{len(res)} passed')
for n_,_,d_ in f: print('  FAIL',n_,'|',d_[:240])
sys.exit(1 if f else 0)
