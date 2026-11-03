"""fastgeodesic.distance must behave exactly like geopy.distance."""

import random

import pytest
from geopy import distance as ref
from geopy.point import Point

from fastgeodesic import distance as fast

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
    for _ in range(20000):
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


@pytest.mark.parametrize("ellipsoid", ["GRS-80", "Intl 1924", (6377.397155, 6356.078963, 1 / 299.1528128)])
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
