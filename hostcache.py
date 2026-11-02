"""Updates still arrive when the host caches files for 10 minutes (as GitHub Pages does)."""
import re, sys
from playwright.sync_api import sync_playwright
import _common
from _common import Report
R = Report('HOST CACHE (10-minute max-age)')
site = _common.copy_site(sys.argv[1])
def edit(marker, version):
    h = re.sub(r'<!--MARK:\w+-->', '', open(site + '/index.html', encoding='utf-8').read()).replace('</body>', f'<!--MARK:{marker}--></body>', 1)
    open(site + '/index.html', 'w', encoding='utf-8').write(h)
    w = re.sub(r"CACHE_VERSION = '[^']*'", f"CACHE_VERSION = '{version}'", open(site + '/sw.js').read()); open(site + '/sw.js', 'w').write(w)
edit('A', 'vA')
BASE, stop = _common.start(site, 'public, max-age=600'); U = BASE + 'index.html'
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); pg = ctx.new_page()
    pg.goto(U); pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(500)
    edit('B', 'vB')   # a new version goes live; the host still hands out the old files from its cache
    pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.update())"); pg.wait_for_timeout(1500)
    R.ck('new version is noticed despite the host cache', not pg.evaluate("document.getElementById('update-banner').hidden"))
    cached = pg.evaluate("caches.open('brew-calculator-vB').then(c=>c.match('./index.html')).then(r=>r?r.text():null)") or ''
    R.ck('the new offline copy is the NEW index.html, not a stale one', 'MARK:B' in cached and 'MARK:A' not in cached)
    with pg.expect_navigation(timeout=8000): pg.click('#btn-update')
    pg.wait_for_timeout(800); R.ck('after updating the page runs the new code', 'MARK:B' in pg.content())
    R.ck('only the new cache is left', pg.evaluate("caches.keys()") == ['brew-calculator-vB'], pg.evaluate("caches.keys()"))
    edit('C', 'vB')   # content changes but the version number was forgotten
    pg.goto(U); pg.wait_for_timeout(600); R.ck('a plain visit after a content-only change shows the newest page', 'MARK:C' in pg.content())
    ctx.set_offline(True); pg.goto(U); pg.wait_for_timeout(500)
    R.ck('offline afterwards still works with the latest copy', 'MARK:C' in pg.content() and pg.is_visible('#view-home'))
    b.close()
stop(); R.finish()
