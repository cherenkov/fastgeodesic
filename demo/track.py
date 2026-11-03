"""デモ用の GPS ログを作る。1秒ごとに記録した山歩きのような軌跡(乱数の種は固定)。"""

import math
import random


def make_track(n, seed=42):
    rnd = random.Random(seed)
    lat, lon = 35.3606, 138.7274  # 富士山頂付近から歩き出す
    heading = rnd.uniform(0, 360)
    pts = [(lat, lon)]
    for _ in range(n - 1):
        heading += rnd.gauss(0, 8)
        step = abs(rnd.gauss(1.1, 0.4))  # 1秒あたり約1.1m
        lat += step * math.cos(math.radians(heading)) / 111_000
        lon += step * math.sin(math.radians(heading)) / (111_000 * math.cos(math.radians(lat)))
        pts.append((lat, lon))
    return pts
