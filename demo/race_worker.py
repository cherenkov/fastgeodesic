"""GPS ログの総距離を geopy で計算する。進み具合を1行ずつ JSON で標準出力に出す。

使い方: python -I race_worker.py <ref|fast> <点の数>
ref は geopy そのまま、fast は fastgeodesic.patch() を1行足しただけ。計算のコードは同じ。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # -I で起動しても隣の track.py を読めるように
from track import make_track  # noqa: E402

impl, n = sys.argv[1], int(sys.argv[2])

if impl == "fast":
    import fastgeodesic

    fastgeodesic.patch()

from geopy import distance

track = make_track(n)
emit_every = max(1, n // 200)


def emit(**kw):
    sys.stdout.write(json.dumps(kw) + "\n")
    sys.stdout.flush()


emit(type="start")
start = time.perf_counter()
total = 0.0
for i in range(1, n):
    # ↓ よくある書き方: 隣り合う2点の距離を1組ずつ足していく
    total += distance.geodesic(track[i - 1], track[i]).meters
    if i % emit_every == 0:
        emit(type="progress", i=i, total=total, ms=(time.perf_counter() - start) * 1e3)
emit(type="done", i=n - 1, total=total, ms=(time.perf_counter() - start) * 1e3)
