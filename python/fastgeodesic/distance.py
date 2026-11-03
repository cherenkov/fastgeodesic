"""Drop-in replacement for ``geopy.distance`` (geopy 2.x).

Replace ``geopy`` with ``fastgeodesic`` in the import::

    from geopy.distance import geodesic        # before
    from fastgeodesic.distance import geodesic  # after

``geodesic`` (and its aliases ``distance`` and ``GeodesicDistance``) is a subclass of
``geopy.distance.geodesic`` whose distances are computed with fastgeodesic. Every other
name in this module (``great_circle``, ``Distance``, ``ELLIPSOIDS``, ...) is geopy's own
object. geopy itself is not modified.
"""

import functools

from geographiclib.geodesic import Geodesic as _RefGeodesic
from geopy import distance as _geopy_distance
from geopy.distance import *  # noqa: F401,F403  (geopy.distance has no __all__: every public name)
from geopy.point import Point

from . import Geodesic as _FastGeodesic


@functools.cache
def _geods(a, f):
    # geopy keeps ellipsoids in kilometers, e.g. (6378.137, 6356.752..., 1/298.257...)
    return _FastGeodesic(a, f), _RefGeodesic(a, f)


_WGS84 = _geopy_distance.ELLIPSOIDS["WGS-84"]
_WGS84_FAST, _WGS84_REF = _geods(_WGS84[0], _WGS84[2])


def _ensure_same_altitude(a, b):
    # Same check and message as geopy.distance._ensure_same_altitude (geopy 2.0 to 2.5),
    # copied so as not to depend on a private geopy name
    if abs(a.altitude - b.altitude) > 1e-6:
        raise ValueError("Calculating distance between points with different altitudes is not supported")


def _plain(p):
    # True for a (lat, lon) tuple or list of in-range numbers, which Point() would accept
    # unchanged. isinstance also accepts numpy.float64, which pandas rows yield.
    # The range checks reject NaN and inf.
    if type(p) not in (tuple, list) or len(p) != 2:
        return False
    lat, lon = p
    return (
        isinstance(lat, (float, int))
        and isinstance(lon, (float, int))
        and not isinstance(lat, bool)
        and not isinstance(lon, bool)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


class geodesic(_geopy_distance.geodesic):
    """Same API and results as ``geopy.distance.geodesic``, computed with fastgeodesic.

    ``.geod`` is a real ``geographiclib.geodesic.Geodesic``, as in geopy, so
    ``destination()`` and anything else that uses it is geopy's own code.
    """

    def measure(self, a, b):
        e = self.ELLIPSOID
        if e is _WGS84:
            fast, self.geod = _WGS84_FAST, _WGS84_REF
        else:
            fast, self.geod = _geods(e[0], e[2])
        # Most common input first: two (lat, lon) tuples of floats
        if type(a) is tuple and type(b) is tuple and len(a) == 2 and len(b) == 2:
            lat1, lon1 = a
            lat2, lon2 = b
            if (
                type(lat1) is float and type(lon1) is float and type(lat2) is float and type(lon2) is float
                and -90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180
            ):
                return fast._s12(lat1, lon1, lat2, lon2)
        if _plain(a) and _plain(b):
            return fast._s12(a[0], a[1], b[0], b[1])
        a, b = Point(a), Point(b)
        _ensure_same_altitude(a, b)
        return fast._s12(a.latitude, a.longitude, b.latitude, b.longitude)


GeodesicDistance = geodesic
distance = geodesic
