"""fastgeodesic のデモ用サーバ。標準ライブラリだけで動く。

起動: .venv/bin/python -I demo/server.py  →  http://127.0.0.1:8790/
"""

import json
import random
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from geographiclib.geodesic import Geodesic as Ref
from geopy import distance

import fastgeodesic
from fastgeodesic import Geodesic as Fast

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # -I で起動しても隣の track.py を読めるように
from track import make_track  # noqa: E402
PORT = 8790


def per_call_us(fn, reps):
    fn()
    best = float("inf")
    for _ in range(3):
        s = time.perf_counter()
        for _ in range(reps):
            fn()
        best = min(best, (time.perf_counter() - s) / reps)
    return best * 1e6


def pair(q):
    lat1, lon1, lat2, lon2 = (float(q[k][0]) for k in ("lat1", "lon1", "lat2", "lon2"))
    ref = Ref.WGS84.Inverse(lat1, lon1, lat2, lon2)
    fast = Fast.WGS84.Inverse(lat1, lon1, lat2, lon2)
    # 地図に描く測地線(高速版の Direct で100分割)
    steps = 100
    path = []
    for i in range(steps + 1):
        p = Fast.WGS84.Direct(lat1, lon1, fast["azi1"], fast["s12"] * i / steps, Fast.STANDARD | Fast.LONG_UNROLL)
        path.append([p["lon2"], p["lat2"]])
    return {
        "ref": ref,
        "fast": fast,
        "identical": ref == fast,
        "diff": {k: abs(ref[k] - fast[k]) for k in ref},
        "us_ref": per_call_us(lambda: Ref.WGS84.Inverse(lat1, lon1, lat2, lon2), 2000),
        "us_fast": per_call_us(lambda: Fast.WGS84.Inverse(lat1, lon1, lat2, lon2), 2000),
        "path": path,
    }


def timed(fn):
    s = time.perf_counter()
    out = fn()
    return (time.perf_counter() - s) * 1e3, out


def bench(q):
    n = max(1000, min(int(q.get("n", ["20000"])[0]), 200000))
    rnd = random.Random(n)
    pts = [(rnd.uniform(-90, 90), rnd.uniform(-180, 180), rnd.uniform(-90, 90), rnd.uniform(-180, 180)) for _ in range(n)]
    cols = [list(c) for c in zip(*pts)]

    t_ref, r_ref = timed(lambda: [Ref.WGS84.Inverse(*c)["s12"] for c in pts])
    t_fast, r_fast = timed(lambda: [Fast.WGS84.Inverse(*c)["s12"] for c in pts])
    t_many, r_many = timed(lambda: fastgeodesic.inverse_many(*cols))

    t_geopy, g_ref = timed(lambda: [distance.geodesic(c[:2], c[2:]).meters for c in pts])
    fastgeodesic.patch()
    try:
        t_geopy_fast, g_fast = timed(lambda: [distance.geodesic(c[:2], c[2:]).meters for c in pts])
    finally:
        fastgeodesic.unpatch()

    def cmp(a, b):
        return {"max_diff_m": max(abs(x - y) for x, y in zip(a, b)), "identical": sum(x == y for x, y in zip(a, b))}

    return {
        "n": n,
        "rows": [
            {"label": "geographiclib Geodesic.Inverse(1組ずつ)", "ref_ms": t_ref, "fast_ms": t_fast, **cmp(r_ref, r_fast)},
            {"label": "geographiclib → inverse_many(まとめて)", "ref_ms": t_ref, "fast_ms": t_many, **cmp(r_ref, r_many)},
            {"label": "geopy distance.geodesic(patch() で差し替え)", "ref_ms": t_geopy, "fast_ms": t_geopy_fast, **cmp(g_ref, g_fast)},
        ],
    }


def race_n(q):
    return max(1000, min(int(q.get("n", ["100000"])[0]), 1_000_000))


def track_preview(q):
    n = race_n(q)
    pts = make_track(n)
    step = max(1, n // 2000)
    return {"n": n, "step": step, "coords": [[lon, lat] for lat, lon in pts[::step]]}


class Handler(BaseHTTPRequestHandler):
    def race(self, q):
        """ワーカーを別プロセスで起動し、進み具合を Server-Sent Events で流す。"""
        impl = q.get("impl", [""])[0]
        if impl not in ("ref", "fast"):
            self.send_error(400, "impl must be ref or fast")
            return
        proc = subprocess.Popen(
            [sys.executable, "-I", str(HERE / "race_worker.py"), impl, str(race_n(q))],
            stdout=subprocess.PIPE,
            text=True,
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for line in proc.stdout:
                self.wfile.write(f"data: {line.strip()}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.kill()
            proc.wait()

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/race":
            self.race(parse_qs(url.query))
            return
        try:
            if url.path == "/":
                body, ctype = (HERE / "index.html").read_bytes(), "text/html; charset=utf-8"
            elif url.path == "/race":
                body, ctype = (HERE / "race.html").read_bytes(), "text/html; charset=utf-8"
            elif url.path == "/api/track":
                body, ctype = json.dumps(track_preview(parse_qs(url.query))).encode(), "application/json"
            elif url.path == "/api/pair":
                body, ctype = json.dumps(pair(parse_qs(url.query))).encode(), "application/json"
            elif url.path == "/api/bench":
                body, ctype = json.dumps(bench(parse_qs(url.query))).encode(), "application/json"
            else:
                self.send_error(404)
                return
        except (KeyError, ValueError) as e:
            self.send_error(400, str(e))
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}/")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
