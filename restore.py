"""A running brew survives reloads and restarts, and bad or stale saved state is ignored."""
import sys
from playwright.sync_api import sync_playwright
from _common import Report
URL = sys.argv[1]; R = Report('TIMER RESTORE'); KEY = 'brewCalculator.brew.v1'
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(300)
    st = lambda: pg.evaluate("[state.engine&&state.engine.status, state.engine&&state.engine.index]")
    pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start'); pg.wait_for_timeout(2200)
    R.ck('running brew is saved', pg.evaluate("!!localStorage.getItem('%s')" % KEY))
    pg.goto(URL); pg.wait_for_timeout(900)
    R.ck('running brew is restored after a reload, on the timer view', st()[0] == 'running' and pg.is_visible('#view-timer') and pg.evaluate("!!tickWorker"), st())
    R.ck('restored brew shows a confirmation and cannot be started twice', 'restored' in pg.inner_text('#toast') and pg.is_disabled('#btn-start'))
    pg.click('#btn-pause'); pg.wait_for_timeout(300); base = pg.evaluate("state.engine.baseMs")
    pg.goto(URL + '#home'); pg.wait_for_timeout(600)
    R.ck('paused brew restored with the same elapsed time, and an explicit #home is respected', st()[0] == 'paused' and abs(pg.evaluate("state.engine.baseMs") - base) < 5 and pg.is_visible('#view-home'))
    pg.evaluate("navigate('timer')"); pg.click('#btn-reset'); pg.wait_for_timeout(250)
    R.ck('reset removes the saved brew', pg.evaluate("localStorage.getItem('%s')" % KEY) is None)
    pg.reload(); pg.wait_for_timeout(400); R.ck('nothing to restore after a reset', st()[0] == 'idle', st())
    # cold brew left overnight: lands on the last step
    pg.evaluate("selectRecipeForBrewing('cold-brew-starter')"); pg.click('#btn-start'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{const k='%s',o=JSON.parse(localStorage.getItem(k));o.eng.startedAt-=(60+43200+30)*1000;localStorage.setItem(k,JSON.stringify(o))}" % KEY)
    pg.goto(URL); pg.wait_for_timeout(700)
    R.ck('a cold brew left for 12 h resumes in the final step', st() == ['running', 2], st())
    # far too old
    pg.evaluate("()=>localStorage.setItem('%s',JSON.stringify({v:1,recipe:state.activeBrew,eng:{status:'running',baseMs:0,startedAt:Date.now()-20*3600e3,index:0,waiting:false}}))" % KEY)
    pg.goto(URL); pg.wait_for_timeout(600)
    R.ck('a brew that ended more than 6 h ago is discarded', st()[0] == 'idle' and pg.evaluate("localStorage.getItem('%s')" % KEY) is None, st())
    # finished while away
    pg.evaluate("selectRecipeForBrewing('espresso-starter')")
    pg.evaluate("()=>localStorage.setItem('%s',JSON.stringify({v:1,recipe:state.activeBrew,eng:{status:'running',baseMs:0,startedAt:Date.now()-600e3,index:0,waiting:false}}))" % KEY)
    pg.goto(URL); pg.wait_for_timeout(700)
    R.ck('a brew that finished while away shows the completion card and clears itself', st()[0] == 'complete' and pg.is_visible('#timer-complete') and pg.evaluate("localStorage.getItem('%s')" % KEY) is None, st())
    # hostile state
    for bad in ['{oops', '{"v":1,"recipe":{"steps":"x"},"eng":{}}', '{"v":1,"recipe":{"steps":[{"duration":-5}]},"eng":{"status":"running","baseMs":0,"startedAt":1,"index":0}}', 'null', '[]']:
        pg.evaluate("v=>localStorage.setItem('%s',v)" % KEY, bad); pg.goto(URL); pg.wait_for_timeout(350)
        R.ck(f'unusable saved state ignored: {bad[:32]}', st()[0] == 'idle' and pg.evaluate("localStorage.getItem('%s')" % KEY) is None, st())
    # manual mode never skips a step, however long the page slept
    pg.evaluate("()=>{state.settings.autoAdvance=false;saveState()}"); pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.click('#btn-start')
    pg.evaluate("()=>{const k='%s',o=JSON.parse(localStorage.getItem(k));o.eng.startedAt-=3600000;localStorage.setItem(k,JSON.stringify(o))}" % KEY)
    pg.goto(URL); pg.wait_for_timeout(600)
    R.ck('manual mode: after a 1 h gap the brew waits at the end of its step', pg.evaluate("[state.engine.status,state.engine.index,state.engine.waiting]") == ['running', 0, True], pg.evaluate("[state.engine.status,state.engine.index,state.engine.waiting]"))
    pg.evaluate("()=>{state.settings.language='id';saveState()}"); pg.goto(URL); pg.wait_for_timeout(600)
    R.ck('restore message is translated', 'dipulihkan' in pg.inner_text('#toast'), pg.inner_text('#toast'))
    R.ck('no console errors', not errs, errs[:2]); b.close()
R.finish()
