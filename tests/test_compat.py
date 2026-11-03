import math
import random

import pytest
from geographiclib.geodesic import Geodesic as Ref

import fastgeodesic
from fastgeodesic import Geodesic as Fast

TOL = {"s12": 1e-8, "m12": 1e-8, "M12": 1e-12, "M21": 1e-12, "S12": 1e-2}
DEG_TOL = 1e-11


def cases(n, seed=1):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        out.append((rnd.uniform(-90, 90), rnd.uniform(-180, 180), rnd.uniform(-90, 90), rnd.uniform(-180, 180)))
    # Edge cases: poles, antimeridian, same point, near-antipodal, out-of-range longitude
    out += [(90, 0, -90, 0), (0, 179.9, 0, -179.9), (35, 139, 35, 139), (0, 0, 0.5, 179.7),
            (-30, 0, 29.9, 179.8), (10, 540, 20, -400), (0, 0, 0, 180), (89.999, 0, -89.999, 180)]
    return out


def close(key, a, b):
    if isinstance(a, float) and math.isnan(a):
        return math.isnan(b)
    tol = TOL.get(key, DEG_TOL)
    return abs(a - b) <= tol * max(1.0, abs(b))


@pytest.mark.parametrize("mask", [Ref.STANDARD, Ref.DISTANCE, Ref.ALL, Ref.STANDARD | Ref.LONG_UNROLL])
def test_inverse_matches(mask):
    for c in cases(20000):
        r, f = Ref.WGS84.Inverse(*c, mask), Fast.WGS84.Inverse(*c, mask)
        assert r.keys() == f.keys(), c
        for k in r:
            assert close(k, f[k], r[k]), (c, k, f[k], r[k])


@pytest.mark.parametrize("mask", [Ref.STANDARD, Ref.LATITUDE | Ref.LONGITUDE, Ref.ALL, Ref.STANDARD | Ref.LONG_UNROLL])
def test_direct_matches(mask):
    rnd = random.Random(2)
    for _ in range(20000):
        c = (rnd.uniform(-90, 90), rnd.uniform(-180, 180), rnd.uniform(-180, 180), rnd.uniform(0, 2e7))
        r, f = Ref.WGS84.Direct(*c, mask), Fast.WGS84.Direct(*c, mask)
        assert r.keys() == f.keys(), c
        for k in r:
            assert close(k, f[k], r[k]), (c, k, f[k], r[k])


def test_other_ellipsoid():
    r, f = Ref(6377397.155, 1 / 299.1528128), Fast(6377397.155, 1 / 299.1528128)  # Bessel 1841
    assert (f.a, f.f) == (r.a, r.f)
    for c in cases(2000, seed=3):
        assert close("s12", f.Inverse(*c)["s12"], r.Inverse(*c)["s12"])


def test_constants_match():
    for name in dir(Ref):
        if name.isupper() and name != "WGS84":
            assert getattr(Fast, name) == getattr(Ref, name), name


def test_geopy_patch():
    from geopy import distance

    pts = cases(5000, seed=4)
    before = [distance.geodesic(c[:2], c[2:]).meters for c in pts if abs(c[0]) <= 90 and abs(c[2]) <= 90]
    fastgeodesic.patch()
    try:
        assert distance.Geodesic is Fast
        after = [distance.geodesic(c[:2], c[2:]).meters for c in pts if abs(c[0]) <= 90 and abs(c[2]) <= 90]
        dest = distance.geodesic(kilometers=100).destination((35.68, 139.77), bearing=45)
    finally:
        fastgeodesic.unpatch()
    assert distance.Geodesic is Ref
    assert all(close("s12", a, b) for a, b in zip(after, before))
    ref_dest = distance.geodesic(kilometers=100).destination((35.68, 139.77), bearing=45)
    assert abs(dest.latitude - ref_dest.latitude) < 1e-11 and abs(dest.longitude - ref_dest.longitude) < 1e-11


def test_inverse_many():
    pts = cases(5000, seed=5)[:5000]
    got = fastgeodesic.inverse_many(*zip(*pts))
    for c, s in zip(pts, got):
        assert close("s12", s, Ref.WGS84.Inverse(*c, Ref.DISTANCE)["s12"])
