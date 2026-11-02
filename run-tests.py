#!/usr/bin/env python3
"""Run every Brew Calculator check against the site folder and print one line per suite.

    python3 tools/tests/run-tests.py                  # everything, against ./brew-calculator-pwa
    python3 tools/tests/run-tests.py --list           # what exists
    python3 tools/tests/run-tests.py --only logic,ui  # a few suites
    python3 tools/tests/run-tests.py --site path/to/site
    python3 tools/tests/run-tests.py --fail-fast

Needs Python 3.8+ and Playwright:   pip install playwright   then   playwright install chromium
Exit code 0 = all passed, 1 = something failed.
"""
import argparse, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _common

# name, file, how it gets the site ('url' = a running server, 'dir' = the folder itself), what it covers
SUITES = [
    ('logic',         'logic.py',         'url', 'calculator maths, built-in recipes, timer engine on a fake clock, stored-data cleaning'),
    ('validation',    'validation.py',    'url', 'strict input rules: numbers, names, ratio, temperature, estimated time'),
    ('ui',            'ui.py',            'url', 'real clicks: calculator, timer, recipes (create/edit/delete), units, settings, languages'),
    ('backup',        'backup.py',        'url', 'export/import of recipes, favorites and settings, with hostile files'),
    ('datasafety',    'datasafety.py',    'url', 'persistent-storage request and the backup reminder'),
    ('alerts',        'alerts.py',        'url', 'vibration, notifications and the background timer worker'),
    ('ics',           'ics.py',           'url', 'calendar reminder files for long brews'),
    ('restore',       'restore.py',       'url', 'a running brew survives reloads; stale or broken saved state is ignored'),
    ('accessibility', 'accessibility.py', 'url', 'headings, titles, contrast, targets, focus, announcements, zoom'),
    ('resilience',    'resilience.py',    'dir', 'corrupt data, blocked storage, offline on every route, update flow'),
    ('hostcache',     'hostcache.py',     'dir', 'updates still arrive behind a host that caches for 10 minutes'),
    ('autoversion',   'autoversion.py',   'dir', 'stamp-version.py behaviour and automatic update detection'),
]


def main():
    ap = argparse.ArgumentParser(description='Run the Brew Calculator test suites.')
    ap.add_argument('--site', default=os.path.join(HERE, '..', '..', 'brew-calculator-pwa'), help='folder with index.html (default: ./brew-calculator-pwa)')
    ap.add_argument('--only', help='comma-separated suite names')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--fail-fast', action='store_true')
    ap.add_argument('--timeout', type=int, default=300, help='seconds per suite')
    a = ap.parse_args()
    if a.list:
        for n, f, m, d in SUITES: print(f'{n:14s} {d}')
        return 0
    site = os.path.abspath(a.site)
    if not os.path.isfile(os.path.join(site, 'index.html')):
        print(f'No index.html in {site}. Pass the site folder with --site.'); return 2
    try:
        import playwright  # noqa: F401
    except ImportError:
        print('Playwright is missing. Install it once with:\n  pip install playwright\n  playwright install chromium'); return 2
    wanted = [s for s in SUITES if not a.only or s[0] in a.only.split(',')]
    if a.only and len(wanted) != len(set(a.only.split(','))):
        print('Unknown suite in --only. Use --list.'); return 2
    results, t_all = [], time.time()
    stamp = os.path.join(HERE, '..', 'stamp-version.py')
    if os.path.isfile(stamp) and not a.only:
        r = subprocess.run([sys.executable, stamp, site, '--check'], capture_output=True, text=True)
        ok = r.returncode == 0
        print(f'{"PASS" if ok else "FAIL"}  version stamp is current' + ('' if ok else f'\n      {r.stdout.strip()}'))
        results.append(('stamp', ok))
    with _common.serve(site) as base:
        for name, file, mode, desc in wanted:
            arg = base + 'index.html' if mode == 'url' else site
            t0 = time.time()
            try:
                r = subprocess.run([sys.executable, os.path.join(HERE, file), arg], capture_output=True, text=True, timeout=a.timeout, cwd=HERE)
                out, code = r.stdout + r.stderr, r.returncode
            except subprocess.TimeoutExpired as e:
                out, code = f'TIMEOUT after {a.timeout}s\n{(e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")}', 1
            m = re.search(r'(\d+)/(\d+) passed', out)
            count = f'{m.group(1)}/{m.group(2)}' if m else 'no result'
            print(f'{"PASS" if code == 0 else "FAIL"}  {name:14s} {count:>8s}  {time.time() - t0:5.1f}s')
            if code != 0:
                lines = [l for l in out.splitlines() if l.strip()]
                keep = [l for l in lines if 'FAIL' in l or 'Error' in l or 'CRASH' in l or 'TIMEOUT' in l][:12] or lines[-8:]
                for l in keep: print('      ' + l[:200])
            results.append((name, code == 0))
            if code != 0 and a.fail_fast: break
    bad = [n for n, ok in results if not ok]
    print(f'\n{len(results) - len(bad)}/{len(results)} suites passed in {time.time() - t_all:.0f}s' + (f'. Failed: {", ".join(bad)}' if bad else '. All good.'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
