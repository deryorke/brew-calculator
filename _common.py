"""Shared helpers for the Brew Calculator test suites (static server, temp files)."""
import contextlib, http.server, os, shutil, socket, sys, tempfile, threading


class _Handler(http.server.SimpleHTTPRequestHandler):
    cache_control = None

    def end_headers(self):
        if self.cache_control:
            self.send_header('Cache-Control', self.cache_control)   # lets a test imitate a host that caches for 10 minutes
        super().end_headers()

    def log_message(self, *args):
        pass


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


def start(directory, cache_control=None):
    """Serve `directory` on a free port. Returns (base_url, stop_function)."""
    handler = type('Handler', (_Handler,), {'cache_control': cache_control})
    server = _Server(('', 0), lambda *a, **k: handler(*a, directory=directory, **k))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    def stop():
        server.shutdown(); server.server_close()
    return f'http://localhost:{server.server_address[1]}/', stop


@contextlib.contextmanager
def serve(directory, cache_control=None):
    url, stop = start(directory, cache_control)
    try:
        yield url
    finally:
        stop()


def tmpdir():
    d = tempfile.mkdtemp(prefix='brew-test-')
    return d


def copy_site(src):
    """A throw-away copy of the site, so tests can edit files without touching the real folder."""
    dst = os.path.join(tmpdir(), 'site')
    shutil.copytree(src, dst)
    return dst


class Report:
    def __init__(self, title):
        self.title, self.rows = title, []

    def ck(self, name, ok, detail=''):
        self.rows.append((name, bool(ok), str(detail)))

    def finish(self):
        fails = [r for r in self.rows if not r[1]]
        print(f'{self.title}: {len(self.rows) - len(fails)}/{len(self.rows)} passed')
        for name, _, detail in fails:
            print('  FAIL', name, '|', detail[:300])
        sys.exit(1 if fails else 0)
