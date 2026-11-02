Brew Calculator tools (not part of the website; do not upload this folder)

stamp-version.py   Run before every upload so phones notice the new version:
                     python3 tools/stamp-version.py
                   Safe to run repeatedly: the version only changes when the files change.
                   --check  exits with 1 when sw.js is out of date.   --print  shows the version only.
tests/             Automated checks (needs: pip install playwright; playwright install chromium):
                     python3 tools/tests/run-tests.py
                   See tools/tests/README.md.
optional/          Ready-made automation for GitHub Pages (github-pages.yml) and Netlify (netlify.toml).
