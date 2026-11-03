"""fastgeodesic.distance must behave exactly like geopy.distance."""

import copy
import importlib
import pickle
import random
from unittest import mock

import pytest
from geopy import distance as ref
from geopy import units
from geopy.point import Point

from fastgeodesic import distance as fast

from conftest import samples

KM_TOL = 1e-11  # kilometers, i.e. 1e-8 m


def same_km(a, b):
    return abs(a - b) <= KM_TOL * max(1.0, abs(b))


INPUTS = [
    ((35.3606, 138.7274), (35.6812, 139.7671)),  # float tuples
    ((35, 138), (36, 140)),  # ints
    ([35.36, 138.72], [35.68, 139.76]),  # lists
    ((-89.9, 179.9), (89.9, -179.9)),  # near poles and antimeridian
    ((0.0, 0.0), (0.5, 179.7)),  # near-antipodal
    ((35.0, 190.0), (35.0, -175.0)),  # longitude out of range, Point normalizes
    ("35.3606, 138.7274", "35.6812 139.7671"),  # strings
    (Point(35.36, 138.72), Point(35.68, 139.76)),  # Point objects
    ((35.36, 138.72, 1.0), (35.68, 139.76, 1.0)),  # same altitude
    ((35.36, 138.72), (35.36, 138.72)),  # same point
]


@pytest.mark.parametrize("a,b", INPUTS)
def test_measure_matches(a, b):
    r, f = ref.geodesic(a, b), fast.geodesic(a, b)
    assert same_km(f.km, r.km), (a, b, f.km, r.km)
    assert same_km(f.miles, r.miles)
    assert isinstance(f, ref.geodesic) and isinstance(f, ref.Distance)


def test_numpy_scalars():
    np = pytest.importorskip("numpy")
    a, b = (np.float64(35.36), np.float64(138.72)), (np.float64(35.68), np.float64(139.76))
    assert same_km(fast.geodesic(a, b).km, ref.geodesic(a, b).km)


def test_random_pairs():
    rnd = random.Random(1)
    for _ in range(samples(20000)):
        a = (rnd.uniform(-90, 90), rnd.uniform(-180, 180))
        b = (rnd.uniform(-90, 90), rnd.uniform(-180, 180))
        assert same_km(fast.geodesic(a, b).km, ref.geodesic(a, b).km), (a, b)


@pytest.mark.parametrize(
    "a,b",
    [
        ((91.0, 0.0), (0.0, 0.0)),  # latitude out of range
        ((35.0, 139.0, 0.0), (35.0, 139.0, 5.0)),  # different altitudes
        ((float("nan"), 0.0), (0.0, 0.0)),
        ("not a point", (0.0, 0.0)),
    ],
)
def test_errors_match(a, b):
    with pytest.raises(Exception) as r:
        ref.geodesic(a, b)
    with pytest.raises(Exception) as f:
        fast.geodesic(a, b)
    assert type(f.value) is type(r.value)
    assert str(f.value) == str(r.value)


def test_multiple_points_and_kwargs():
    pts = [(35.0, 139.0), (35.1, 139.1), (35.2, 139.0)]
    assert same_km(fast.geodesic(*pts).km, ref.geodesic(*pts).km)
    assert same_km(fast.geodesic(*pts, kilometers=1).km, ref.geodesic(*pts, kilometers=1).km)
    assert fast.geodesic(kilometers=5).km == ref.geodesic(kilometers=5).km


@pytest.mark.parametrize("ellipsoid", ["GRS-80", "Intl 1924", (6377.397155, 6356.078963, 1 / 299.1528128), [6377.397155, 6356.078963, 1 / 299.1528128]])
def test_other_ellipsoids(ellipsoid):
    a, b = (35.36, 138.72), (40.64, -73.77)
    assert same_km(fast.geodesic(a, b, ellipsoid=ellipsoid).km, ref.geodesic(a, b, ellipsoid=ellipsoid).km)


def test_destination():
    for start, bearing, km in [((35.68, 139.77), 45, 100), ((-33.9, 151.2), 270, 12000), ((89.0, 0.0), 180, 50)]:
        r = ref.geodesic(kilometers=km).destination(start, bearing)
        f = fast.geodesic(kilometers=km).destination(start, bearing)
        assert abs(f.latitude - r.latitude) < 1e-11 and abs(f.longitude - r.longitude) < 1e-11
    r = ref.geodesic().destination((35.0, 139.0), 90, distance=10)
    f = fast.geodesic().destination((35.0, 139.0), 90, distance=10)
    assert abs(f.longitude - r.longitude) < 1e-11


def test_arithmetic_and_compare():
    a, b = (35.0, 139.0), (36.0, 140.0)
    f, r = fast.geodesic(a, b), ref.geodesic(a, b)
    assert same_km((f + r).km, 2 * r.km)
    assert same_km((f * 2).km, (r * 2).km)
    assert abs(f - r).km < KM_TOL


def test_aliases_and_passthrough():
    assert fast.distance is fast.geodesic and fast.GeodesicDistance is fast.geodesic
    assert fast.great_circle is ref.great_circle
    assert fast.Distance is ref.Distance
    assert fast.ELLIPSOIDS is ref.ELLIPSOIDS


def test_geopy_untouched():
    from geographiclib.geodesic import Geodesic

    assert ref.geodesic is not fast.geodesic
    assert ref.Geodesic is Geodesic


def test_pickle_and_copy():
    f = fast.geodesic((35.0, 139.0), (36.0, 140.0), ellipsoid="GRS-80")
    for g in (pickle.loads(pickle.dumps(f)), copy.deepcopy(f), copy.copy(f)):
        assert g.km == f.km and g.ELLIPSOID == f.ELLIPSOID
        assert same_km(g.destination((35.0, 139.0), 45).latitude, f.destination((35.0, 139.0), 45).latitude)


def test_geod_is_geographiclib():
    from geographiclib.geodesic import Geodesic

    f, r = fast.geodesic((35.0, 139.0), (36.0, 140.0)), ref.geodesic((35.0, 139.0), (36.0, 140.0))
    assert type(f.geod) is Geodesic and (f.geod.a, f.geod.f) == (r.geod.a, r.geod.f)
    assert hasattr(f.geod, "InverseLine")


def test_ellipsoid_assigned_directly():
    f = fast.geodesic()
    f.ELLIPSOID = ref.ELLIPSOIDS["GRS-80"]
    r = ref.geodesic(ellipsoid="GRS-80")
    a, b = (35.36, 138.72), (40.64, -73.77)
    assert same_km(f.measure(a, b), r.measure(a, b))


def test_star_import_and_dir():
    ns_ref, ns_fast = {}, {}
    exec("from geopy.distance import *", ns_ref)
    exec("from fastgeodesic.distance import *", ns_fast)
    assert set(ns_ref) - {"__builtins__"} <= set(ns_fast)
    assert ns_fast["geodesic"] is fast.geodesic
    assert all(ns_fast[n] is ns_ref[n] for n in ns_ref if n not in ("__builtins__", "geodesic", "GeodesicDistance", "distance"))
    assert {"great_circle", "lonlat", "ELLIPSOIDS"} <= set(dir(fast))
    with pytest.raises(AttributeError, match="fastgeodesic.distance"):
        fast.no_such_name


def test_core_geodesic_pickle():
    from fastgeodesic import Geodesic

    g = pickle.loads(pickle.dumps(Geodesic(6377397.155, 1 / 299.1528128)))
    assert type(g) is Geodesic and (g.a, g.f) == (6377397.155, 1 / 299.1528128)
    assert pickle.loads(pickle.dumps(Geodesic.WGS84)).Inverse(35, 139, 36, 140) == Geodesic.WGS84.Inverse(35, 139, 36, 140)


def test_fast_init_matches_geopy_attributes():
    for a, b in [((35.36, 138.72), (35.68, 139.76)), ((-89.9, 179.9), (89.9, -179.9))]:
        f, r = fast.geodesic(a, b), ref.geodesic(a, b)
        assert set(vars(f)) == set(vars(r))
        assert (f.ellipsoid_key, f.ELLIPSOID) == (r.ellipsoid_key, r.ELLIPSOID)
        assert (f.geod.a, f.geod.f) == (r.geod.a, r.geod.f)
        assert same_km(f.km, r.km)
        assert f.m == f.meters
        assert f.meters == pytest.approx(r.meters, rel=1e-12, abs=1e-8)


def test_meters_formula_matches_geopy_units():
    for km in [0.0, -0.0, 1e-9, 1.5, 12345.678, -3.0]:
        m = fast.geodesic(km).meters
        assert m == units.meters(kilometers=km)
        assert str(m) == str(ref.geodesic(km).meters)


def test_subclass_uses_its_own_measure():
    class Mine(fast.geodesic):
        def measure(self, a, b):
            return 42.0

    assert Mine((35.0, 139.0), (36.0, 140.0)).km == 42.0


def test_ellipsoids_replaced_at_runtime():
    other = (6377.397155, 6356.078963, 1 / 299.1528128)
    a, b = (1.0, 2.0), (3.0, 4.0)
    with mock.patch.dict(ref.ELLIPSOIDS, {"WGS-84": other}):
        expected = ref.geodesic(a, b).km
        assert same_km(fast.geodesic(a, b).km, expected)
        assert same_km(fast.geodesic((1, 2), (3, 4)).km, expected)


def test_mocked_methods_are_used():
    with mock.patch.object(fast.geodesic, "measure", return_value=1.0):
        assert fast.geodesic((1.0, 2.0), (3.0, 4.0)).km == 1.0
    calls = []

    def spy(self, ellipsoid):
        calls.append(ellipsoid)
        ref.geodesic.set_ellipsoid(self, ellipsoid)

    with mock.patch.object(fast.geodesic, "set_ellipsoid", spy):
        fast.geodesic((1.0, 2.0), (3.0, 4.0))
    assert calls == ["WGS-84"]


def test_meters_follows_overridden_kilometers():
    class Corrected(fast.geodesic):
        @property
        def kilometers(self):
            return 2.0

    assert Corrected((1.0, 2.0), (3.0, 4.0)).meters == 2000.0


def test_unknown_geopy_version_falls_back_to_geopy_init():
    import geopy

    import fastgeodesic.distance as mod

    try:
        with mock.patch.object(geopy, "__version__", "2.6.0"):
            importlib.reload(mod)
            assert "__init__" not in vars(mod.geodesic) and "meters" not in vars(mod.geodesic)
            a, b = (35.36, 138.72), (35.68, 139.76)
            assert same_km(mod.geodesic(a, b).km, ref.geodesic(a, b).km)
            assert mod.geodesic(a, b).meters == ref.geodesic(a, b).meters
    finally:
        importlib.reload(mod)
    assert "__init__" in vars(mod.geodesic)
