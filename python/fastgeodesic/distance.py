"""Drop-in replacement for ``geopy.distance``.

Replace ``geopy`` with ``fastgeodesic`` in the import::

    from geopy.distance import geodesic        # before
    from fastgeodesic.distance import geodesic  # after

``geodesic`` (and its aliases ``distance`` and ``GeodesicDistance``) is a subclass of
``geopy.distance.geodesic`` that computes with fastgeodesic. Everything else in this
module (``great_circle``, ``Distance``, ``ELLIPSOIDS``, ...) is geopy's own object.
geopy itself is not modified.
"""

import math

from geopy import distance as _geopy_distance
from geopy.point import Point

from . import Geodesic

__all__ = ["geodesic", "GeodesicDistance", "distance"]

_ensure_same_altitude = _geopy_distance._ensure_same_altitude
_geods = {}


def _geod(ellipsoid):
    # geopy keeps ellipsoids in kilometers, e.g. (6378.137, 6356.752..., 1/298.257...)
    key = (ellipsoid[0], ellipsoid[2])
    g = _geods.get(key)
    if g is None:
        g = _geods[key] = Geodesic(ellipsoid[0], ellipsoid[2])
    return g


def _plain(p):
    # True for a (lat, lon) tuple or list of in-range numbers, which Point() would
    # accept unchanged. Anything else goes through Point() as in geopy.
    if type(p) not in (tuple, list) or len(p) != 2:
        return False
    lat, lon = p
    # isinstance also accepts numpy.float64 (a float subclass), which pandas rows yield
    return (
        isinstance(lat, (float, int))
        and isinstance(lon, (float, int))
        and type(lat) is not bool
        and type(lon) is not bool
        and -90 <= lat <= 90
        and -180 <= lon <= 180
        and math.isfinite(lon)
    )


class geodesic(_geopy_distance.geodesic):
    """Same API and results as ``geopy.distance.geodesic``, computed with fastgeodesic."""

    def measure(self, a, b):
        geod = self.geod = _geod(self.ELLIPSOID)
        if _plain(a) and _plain(b):
            return geod._s12(float(a[0]), float(a[1]), float(b[0]), float(b[1]))
        a, b = Point(a), Point(b)
        _ensure_same_altitude(a, b)
        return geod._s12(a.latitude, a.longitude, b.latitude, b.longitude)

    def destination(self, point, bearing, distance=None):
        point = Point(point)
        if distance is None:
            distance = self
        if isinstance(distance, _geopy_distance.Distance):
            distance = distance.kilometers
        geod = self.geod = _geod(self.ELLIPSOID)
        r = geod.Direct(point.latitude, point.longitude, bearing, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
        return Point(r["lat2"], r["lon2"])


GeodesicDistance = geodesic
distance = geodesic


def __getattr__(name):
    # great_circle, Distance, ELLIPSOIDS, lonlat, ... come straight from geopy
    return getattr(_geopy_distance, name)
