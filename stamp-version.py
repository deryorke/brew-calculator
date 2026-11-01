#!/usr/bin/env python3
"""Give sw.js a version that is computed from the app's own files.

Why: phones only notice a new version when sw.js changes. Instead of bumping CACHE_VERSION by hand,
run this before every upload. The version only changes when the files really change, so running it
twice (or with nothing edited) leaves sw.js untouched.

Usage (from the folder that contains brew-calculator-pwa/ and tools/):
    python3 tools/stamp-version.py                      # stamp ./brew-calculator-pwa
    python3 tools/stamp-version.py path/to/site         # stamp another folder
    python3 tools/stamp-version.py --check              # exit 1 if sw.js is out of date (for CI)
    python3 tools/stamp-version.py --print              # only show the version it would write
"""
import hashlib, os, re, sys

TEXT_EXT = {'.html', '.js', '.webmanifest', '.svg', '.json', '.css', '.txt'}
VERSION_RE = re.compile(r"(const CACHE_VERSION = ')([^']*)(';)")


def read_normalised(path):
    data = open(path, 'rb').read()
    if os.path.splitext(path)[1].lower() in TEXT_EXT:
        data = data.replace(b'\r\n', b'\n')      # same hash on Windows and Unix checkouts
    return data


def compute_version(site):
    sw_path = os.path.join(site, 'sw.js')
    sw = open(sw_path, encoding='utf-8').read()
    shell = re.search(r"const SHELL = \[(.*?)\];", sw, re.S)
    if not shell or not VERSION_RE.search(sw):
        sys.exit('sw.js does not look like the Brew Calculator service worker (SHELL or CACHE_VERSION missing).')
    names = {'sw.js'}
    for entry in re.findall(r"'\./([^']*)'", shell.group(1)):
        if entry and not entry.endswith('/'):
            names.add(entry)
    h = hashlib.sha256()
    for name in sorted(names):
        path = os.path.join(site, name)
        if not os.path.isfile(path):
            sys.exit(f'Missing file listed in sw.js: {name}')
        data = read_normalised(path)
        if name == 'sw.js':                       # ignore the version line itself, or the hash would chase its own tail
            data = VERSION_RE.sub(lambda m: m.group(1) + m.group(3), data.decode('utf-8')).encode('utf-8')
        h.update(name.encode() + b'\0' + data + b'\0')
    return 'c' + h.hexdigest()[:10], sw_path, sw


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    here = os.path.dirname(os.path.abspath(__file__))
    site = args[0] if args else os.path.join(here, '..', 'brew-calculator-pwa')
    if not os.path.isdir(site):
        sys.exit(f'Folder not found: {site}')
    version, sw_path, sw = compute_version(site)
    current = VERSION_RE.search(sw).group(2)
    if '--print' in flags:
        print(version); return
    if current == version:
        print(f'sw.js already at {version}: nothing to do.'); return
    if '--check' in flags:
        print(f'sw.js is out of date (has {current}, files say {version}). Run: python3 tools/stamp-version.py')
        sys.exit(1)
    open(sw_path, 'w', encoding='utf-8', newline='').write(VERSION_RE.sub(lambda m: m.group(1) + version + m.group(3), sw, count=1))
    print(f'sw.js version: {current} -> {version}')


if __name__ == '__main__':
    main()
