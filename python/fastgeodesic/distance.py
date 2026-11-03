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

import geopy
from geographiclib.geodesic import Geodesic as _RefGeodesic
from geopy import distance as _geopy_distance
from geopy import units as _units
from geopy.distance import *  # noqa: F401,F403  (geopy.distance has no __all__: every public name)
from geopy.point import Point

from . import Geodesic as _FastGeodesic


@functools.cache
def _geods(a, f):
    # geopy keeps ellipsoids in kilometers, e.g. (6378.137, 6356.752..., 1/298.257...)
    return _FastGeodesic(a, f), _RefGeodesic(a, f)


_ELLIPSOIDS = _geopy_distance.ELLIPSOIDS
_WGS84 = _ELLIPSOIDS["WGS-84"]
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
        and -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
    )


def _measure(self, a, b):
    e = self.ELLIPSOID
    if e is _WGS84:
        fast, self.geod = _WGS84_FAST, _WGS84_REF
    else:
        fast, self.geod = _geods(e[0], e[2])
    # Most common input first: two (lat, lon) tuples of floats (numpy.float64 is a float subclass)
    if type(a) is tuple and type(b) is tuple and len(a) == 2 and len(b) == 2:
        lat1, lon1 = a
        lat2, lon2 = b
        if (
            isinstance(lat1, float) and isinstance(lon1, float) and isinstance(lat2, float) and isinstance(lon2, float)
            # float bounds: comparing float with int is slower in CPython
            and -90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0 and -180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0
        ):
            return fast._s12(lat1, lon1, lat2, lon2)
    if _plain(a) and _plain(b):
        return fast._s12(a[0], a[1], b[0], b[1])
    a, b = Point(a), Point(b)
    _ensure_same_altitude(a, b)
    return fast._s12(a.latitude, a.longitude, b.latitude, b.longitude)


_set_ellipsoid = _geopy_distance.geodesic.set_ellipsoid


def _known_geopy():
    # __init__ and meters below repeat geopy internals that are identical in geopy 2.0 to 2.5.
    # On any other version geodesic keeps geopy's own __init__ and meters (only measure is ours).
    try:
        major, minor = (int(x) for x in geopy.__version__.split(".")[:2])
    except ValueError:
        return False
    return major == 2 and minor <= 5


_KNOWN_GEOPY = _known_geopy()


class geodesic(_geopy_distance.geodesic):
    """Same API and results as ``geopy.distance.geodesic``, computed with fastgeodesic.

    ``.geod`` is a real ``geographiclib.geodesic.Geodesic``, as in geopy, so
    ``destination()`` and anything else that uses it is geopy's own code.
    """

    measure = _measure

    def __init__(self, *args, **kwargs):
        # The same steps as geodesic.__init__ and Distance.__init__ in geopy 2.0 to 2.5.
        cls = type(self)
        if len(args) == 2 and not kwargs and cls.measure is _measure and cls.set_ellipsoid is _set_ellipsoid:
            # geodesic(a, b) with neither keywords nor overridden or mocked methods:
            # what set_ellipsoid("WGS-84") and one measure() call would do, inlined
            e = _ELLIPSOIDS["WGS-84"]
            self.ellipsoid_key = "WGS-84"
            self.ELLIPSOID = e
            major, minor, f = e  # like geopy: fails unless the ellipsoid has 3 values
            self._Distance__kilometers = _measure(self, args[0], args[1]) + 0.0
            return
        self.ellipsoid_key = None
        self.ELLIPSOID = None
        self.geod = None
        self.set_ellipsoid(kwargs.pop("ellipsoid", "WGS-84"))
        major, minor, f = self.ELLIPSOID  # like geopy: fails unless the ellipsoid has 3 values
        kilometers = kwargs.pop("kilometers", 0)
        if len(args) == 1:
            kilometers += args[0]
        elif len(args) > 1:
            # util.pairwise() in geopy
            for i in range(len(args) - 1):
                kilometers += self.measure(args[i], args[i + 1])
        kilometers += _units.kilometers(**kwargs)
        self._Distance__kilometers = kilometers

    @property
    def meters(self):
        # geopy.units.meters(kilometers=km) is (km + 0.0) * 1000 in geopy 2.0 to 2.5;
        # inlined because the call is a sixth of the time of geodesic(a, b).meters
        return (self.kilometers + 0.0) * 1000

    if not _KNOWN_GEOPY:
        del __init__, meters  # fall back to geopy's own


GeodesicDistance = geodesic
distance = geodesic
