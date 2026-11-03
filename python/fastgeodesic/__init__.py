"""Drop-in Rust replacement for geographiclib.geodesic.Geodesic and geopy.distance.geodesic."""

from ._core import Geodesic as _CoreGeodesic, WGS84_A, WGS84_F

__all__ = ["Geodesic", "patch", "unpatch", "inverse_many"]


class Geodesic(_CoreGeodesic):
    """Same API and results as geographiclib.geodesic.Geodesic."""

    # Same outmask constants as geographiclib.geodesic.Geodesic
    CAP_NONE = 0
    CAP_C1 = 1 << 0
    CAP_C1p = 1 << 1
    CAP_C2 = 1 << 2
    CAP_C3 = 1 << 3
    CAP_C4 = 1 << 4
    CAP_ALL = 0x1F
    CAP_MASK = CAP_ALL
    OUT_ALL = 0x7F80
    OUT_MASK = 0xFF80
    EMPTY = 0
    LATITUDE = 1 << 7 | CAP_NONE
    LONGITUDE = 1 << 8 | CAP_C3
    AZIMUTH = 1 << 9 | CAP_NONE
    DISTANCE = 1 << 10 | CAP_C1
    STANDARD = LATITUDE | LONGITUDE | AZIMUTH | DISTANCE
    DISTANCE_IN = 1 << 11 | CAP_C1 | CAP_C1p
    REDUCEDLENGTH = 1 << 12 | CAP_C1 | CAP_C2
    GEODESICSCALE = 1 << 13 | CAP_C1 | CAP_C2
    AREA = 1 << 14 | CAP_C4
    LONG_UNROLL = 1 << 15
    ALL = OUT_ALL | CAP_ALL
    GEOGRAPHICLIB_GEODESIC_ORDER = 6

    WGS84: "Geodesic"


Geodesic.WGS84 = Geodesic(WGS84_A, WGS84_F)


def inverse_many(lat1, lon1, lat2, lon2):
    """Distances in meters on WGS84 for many pairs at once (not in geographiclib)."""
    return Geodesic.WGS84.inverse_many(list(lat1), list(lon1), list(lat2), list(lon2))


_saved = {}


def patch():
    """Make geographiclib and geopy use fastgeodesic. Undo with unpatch()."""
    import importlib

    for modname in ("geographiclib.geodesic", "geopy.distance"):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue
        if modname not in _saved:
            _saved[modname] = mod.Geodesic
        mod.Geodesic = Geodesic


def unpatch():
    """Undo patch()."""
    import importlib

    for modname, original in list(_saved.items()):
        importlib.import_module(modname).Geodesic = original
        del _saved[modname]
