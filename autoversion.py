# end-to-end: stamp tool + automatic update detection, with NO manual version edit
import subprocess,time,shutil,re,os,json,sys
import _common
from playwright.sync_api import sync_playwright
res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
site=_common.copy_site(sys.argv[1])
tool=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','stamp-version.py')
run=lambda *a: subprocess.run(['python3',tool,site,*a],capture_output=True,text=True)
ver=lambda: re.search(r"CACHE_VERSION = '([^']*)'",open(site+'/sw.js').read()).group(1)
# --- tool behaviour
v0=ver(); r=run(); ck('stamp is idempotent on a stamped site','nothing to do' in r.stdout and ver()==v0,r.stdout+r.stderr)
ck('--check passes when up to date',run('--check').returncode==0)
open(site+'/index.html','a').write('\n<!-- tweak -->'); ck('--check fails after an edit (exit 1)',run('--check').returncode==1)
r=run(); v1=ver(); ck('editing index.html changes the version',v1!=v0 and r.returncode==0,(v0,v1))
c1=open(site+'/index.html','rb').read(); open(site+'/index.html','ab').write(b'<!-- other -->'); run(); v2=ver()
open(site+'/index.html','wb').write(c1); run(); ck('same content -> same version again (deterministic)',v2!=v1 and ver()==v1,(v1,v2,ver()))
open(site+'/index.html','wb').write(c1.replace(b'\n',b'\r\n')); run(); ck('CRLF vs LF checkout gives the same version',ver()==v1,(ver(),v1)); open(site+'/index.html','wb').write(c1); run()
shutil.copy(site+'/icons/icon-192.png',site+'/icons/bak.png'); open(site+'/icons/icon-192.png','ab').write(b'x'); run(); ck('changing a cached icon changes the version',ver()!=v1); shutil.move(site+'/icons/bak.png',site+'/icons/icon-192.png'); run()
open(site+'/screenshots/narrow-home.png','ab').write(b'x'); before=ver(); run(); ck('screenshots (not cached) do not affect the version',ver()==before)
os.remove(site+'/icons/icon-512.png'); r=run(); ck('missing precached file is reported, not silently ignored',r.returncode!=0 and 'icon-512' in (r.stdout+r.stderr),r.stdout+r.stderr); shutil.copy(os.path.join(sys.argv[1],'icons','icon-512.png'),site+'/icons/icon-512.png')
r=subprocess.run(['python3',tool,'/nonexistent'],capture_output=True,text=True); ck('bad folder gives a clear message',r.returncode!=0 and 'not found' in (r.stdout+r.stderr).lower())
run(); base=ver()
# --- browser: install, publish a change WITHOUT touching the version by hand, expect the banner
BASE,_stop=_common.start(site,'public, max-age=600')   # a host that caches for 10 minutes
U=BASE+'index.html'
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(U); pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(600)
    pg.evaluate("navigate('settings')"); pg.wait_for_timeout(500); t=pg.inner_text('#app-version') if pg.is_visible('#app-version') else ''
    ck('Settings shows the running version',base in t,(t,base))
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.update())"); pg.wait_for_timeout(1000); ck('no change -> no banner',pg.evaluate("document.getElementById('update-banner').hidden"))
    _h=open(site+'/index.html').read().replace('</body>','<!-- release 2 --></body>',1); open(site+'/index.html','w').write(_h); run()   # "I edited the app and ran the stamp tool"
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.update())"); pg.wait_for_timeout(1800)
    ck('after stamping, the update banner appears with no manual version edit',not pg.evaluate("document.getElementById('update-banner').hidden"))
    t_old=pg.inner_text('#app-version') if pg.is_visible('#app-version') else ''
    with pg.expect_navigation(timeout=8000): pg.click('#btn-update')
    pg.wait_for_timeout(900); pg.evaluate("navigate('settings')"); pg.wait_for_timeout(600)
    ck('after updating, Settings shows the new version and the page has the new code',ver() in pg.inner_text('#app-version') and 'release 2' in pg.content(),(pg.inner_text('#app-version'),ver()))
    ck('old cache removed',pg.evaluate("caches.keys()")==[f'brew-calculator-{ver()}'],pg.evaluate("caches.keys()"))
    # forgetting the tool: content-only change still reaches users on the next plain visit
    _h=open(site+'/index.html').read().replace('release 2','release 3'); open(site+'/index.html','w').write(_h)
    pg.goto(U); pg.wait_for_timeout(600); ck('even if the tool is forgotten, a normal visit still loads the newest page',('release 3' in pg.content()))
    ck('no console errors',not errs,errs[:2]); b.close()
_stop()
f=[r for r in res if not r[1]]; print(f'AUTO-VERSION: {len(res)-len(f)}/{len(res)} passed')
for n,_,d in f: print('  FAIL',n,'|',d[:220])
sys.exit(1 if f else 0)
