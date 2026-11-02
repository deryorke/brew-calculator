"""Calendar reminders (.ics) for long brews: when the button shows, what the file contains, and that it is well formed."""
import os, re, sys, tempfile
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from _common import Report
URL = sys.argv[1]; R = Report('CALENDAR REMINDER (.ics)'); TMP = tempfile.mkdtemp(prefix='brew-test-')
def unfold(raw): return re.sub(r'\r\n[ \t]', '', raw)
def stamps(raw): return [datetime.strptime(m, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).timestamp() for m in re.findall(r'^DTSTART:(\d{8}T\d{6}Z)\r?$', unfold(raw), re.M)]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(accept_downloads=True); pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(300)
    pg.evaluate("selectRecipeForBrewing('espresso-starter')"); pg.wait_for_timeout(200)
    R.ck('short brew (espresso): no reminder button', pg.evaluate("document.getElementById('ics-row').hidden"))
    pg.evaluate("selectRecipeForBrewing('v60-classic')"); pg.wait_for_timeout(200)
    R.ck('3-minute V60: no reminder button either', pg.evaluate("document.getElementById('ics-row').hidden"))
    pg.evaluate("selectRecipeForBrewing('cold-brew-starter')"); pg.wait_for_timeout(300)
    R.ck('cold brew (12 h): reminder button and hint are shown', not pg.evaluate("document.getElementById('ics-row').hidden") and not pg.evaluate("document.getElementById('long-hint').hidden"))
    t0 = pg.evaluate("Date.now()") / 1000
    with pg.expect_download() as d: pg.click('#btn-ics')
    path = os.path.join(TMP, 'r.ics'); d.value.save_as(path); raw = open(path, 'rb').read().decode()
    R.ck('file name is brew-reminder-….ics', re.fullmatch(r'brew-reminder-\d{12}\.ics', d.value.suggested_filename) is not None, d.value.suggested_filename)
    R.ck('calendar envelope is valid (CRLF, BEGIN/END pairs)', raw.startswith('BEGIN:VCALENDAR\r\n') and raw.endswith('END:VCALENDAR\r\n') and raw.count('BEGIN:VEVENT') == raw.count('END:VEVENT') == 2 and raw.count('BEGIN:VALARM') == 2 and '\n' not in raw.replace('\r\n', ''))
    R.ck('no line is longer than 75 bytes', max(len(l.encode()) for l in raw.split('\r\n')) <= 75)
    R.ck('every event has its own UID', len(set(re.findall(r'^UID:(.+)$', raw, re.M))) == 2)
    s = stamps(raw)
    R.ck('first alert = end of the 12 h steep (about 12 h 1 min from now)', len(s) == 2 and abs((s[0] - t0) - (60 + 43200)) < 20, [x - t0 for x in s])
    R.ck('second alert = brew ready, 5 minutes after the steep', len(s) == 2 and abs((s[1] - s[0]) - 300) < 2, [x - t0 for x in s])
    R.ck('alarms fire exactly at the event start', raw.count('TRIGGER:PT0S') == 2)
    R.ck('titles name the recipe and the step', 'Steep finished' in unfold(raw) and 'is ready' in unfold(raw), unfold(raw)[:300])
    R.ck('button reminds that times assume starting now', 'start now' in pg.inner_text('#toast'), pg.inner_text('#toast'))
    # running brew: remaining time counts down
    pg.click('#btn-start'); pg.wait_for_timeout(2600); t1 = pg.evaluate("Date.now()") / 1000
    with pg.expect_download() as d2: pg.click('#btn-ics')
    path2 = os.path.join(TMP, 'r2.ics'); d2.value.save_as(path2); s2 = stamps(open(path2).read())
    R.ck('running brew: alerts are computed from the time left, not from zero', len(s2) == 2 and abs((s2[0] - t1) - (60 + 43200 - 2.6)) < 6, [x - t1 for x in s2])
    R.ck('no "start now" caveat once the timer is running', 'start now' not in pg.inner_text('#toast'))
    # text escaping and folding (pure function)
    out = pg.evaluate("buildIcs([{at:Date.UTC(2026,10,1,8,0,0),title:'Kopi, \"enak\"; baris\\nbaru ☕ '+'x'.repeat(120),note:'a\\\\b'}],0)")
    lines = out.split('\r\n'); u = unfold(out)
    R.ck('commas, semicolons, newlines and backslashes are escaped', 'Kopi\\, "enak"\\; baris\\nbaru ☕' in u and 'DESCRIPTION:a\\\\b' in u, u[200:360])
    R.ck('long lines are folded with a leading space, emoji never split', all(len(l.encode()) <= 75 for l in lines) and all(l.startswith(' ') for l in lines if l and lines.index(l) > 0 and not re.match(r'^[A-Z-]+[:;]', l)))
    # language
    pg.evaluate("()=>{state.settings.language='id';applySettings();navigate('timer')}"); pg.wait_for_timeout(200)
    R.ck('button is translated', pg.inner_text('#btn-ics') == 'Tambah pengingat (.ics)', pg.inner_text('#btn-ics'))
    R.ck('no console errors', not errs, errs[:2]); b.close()
R.finish()
