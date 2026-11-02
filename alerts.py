"""Vibration, notifications and the background ticker (permission, hidden page and vibration are simulated)."""
import sys
from playwright.sync_api import sync_playwright
from _common import Report
URL = sys.argv[1]; R = Report('ALERTS')
INIT = """
window.__vib=[]; window.__notes=[]; window.__perm='default';
Object.defineProperty(navigator,'vibrate',{value:(p)=>{window.__vib.push(p);return true},configurable:true});
Object.defineProperty(Notification,'permission',{get:()=>window.__perm});
Notification.requestPermission=async()=>{window.__perm='granted';return 'granted'};
ServiceWorkerRegistration.prototype.showNotification=async function(t,o){window.__notes.push([t,o.body])};
"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    pg.add_init_script(INIT); pg.goto(URL); pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(500)
    pg.evaluate("navigate('settings')")
    R.ck('vibration and notification switches exist and start sensibly', pg.is_enabled('#set-vibrate') and pg.is_checked('#set-vibrate') and pg.is_enabled('#set-notify') and not pg.is_checked('#set-notify'))
    pg.click('#set-notify'); pg.wait_for_timeout(300)
    R.ck('turning notifications on asks for permission and keeps the switch on', pg.is_checked('#set-notify') and pg.evaluate("state.settings.notify") and pg.evaluate("__perm") == 'granted')
    pg.evaluate("__vib.length=0"); pg.click('#set-vibrate'); pg.click('#set-vibrate'); R.ck('switching vibration on gives a short test buzz', pg.evaluate("__vib.length") == 1, pg.evaluate("__vib"))
    pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start'); pg.wait_for_timeout(400)
    R.ck('a Web Worker drives the timer while running', pg.evaluate("!!tickWorker"))
    pg.evaluate("__vib.length=0; __notes.length=0")
    pg.click('#btn-skip'); pg.wait_for_timeout(300)
    R.ck('step change vibrates once with the short pattern', pg.evaluate("__vib") == [[200]], pg.evaluate("__vib"))
    R.ck('no notification while the page is visible', pg.evaluate("__notes.length") == 0)
    pg.evaluate("Object.defineProperty(document,'visibilityState',{get:()=>'hidden',configurable:true})")
    pg.click('#btn-reset'); pg.click('#btn-start'); pg.wait_for_timeout(300); pg.evaluate("__vib.length=0; __notes.length=0")
    pg.evaluate("state.settings.autoAdvance=true"); pg.click('#btn-skip'); pg.wait_for_timeout(300)
    n = pg.evaluate("__notes")
    R.ck('hidden page: a step change posts a notification with the instruction', len(n) == 1 and len(n[0][0]) > 2 and len(n[0][1]) > 5, n)
    pg.click('#btn-skip'); pg.wait_for_timeout(400)
    n = pg.evaluate("__notes")
    R.ck('finishing posts a "Brew complete" notification and the long vibration', any('complete' in x[0].lower() for x in n) and [400, 150, 400, 150, 400] in pg.evaluate("__vib"), (n, pg.evaluate("__vib")))
    R.ck('the worker stops when the brew is complete', pg.evaluate("!tickWorker"))
    pg.evaluate("Object.defineProperty(document,'visibilityState',{get:()=>'visible',configurable:true})")
    pg.evaluate("navigate('settings')"); pg.click('#set-vibrate'); pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start'); pg.evaluate("__vib.length=0"); pg.click('#btn-skip'); pg.wait_for_timeout(300)
    R.ck('with vibration switched off nothing vibrates', pg.evaluate("__vib.length") == 0, pg.evaluate("__vib"))
    pg.evaluate("Object.defineProperty(document,'visibilityState',{get:()=>'hidden',configurable:true})"); pg.evaluate("__notes.length=0"); pg.evaluate("state.settings.notify=false"); pg.click('#btn-skip'); pg.wait_for_timeout(300)
    R.ck('with notifications switched off nothing is posted', pg.evaluate("__notes.length") == 0, pg.evaluate("__notes"))
    R.ck('no console errors', not errs, errs[:2]); b.close()
R.finish()
