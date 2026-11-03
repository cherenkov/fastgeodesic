# fastgeodesic

Drop-in Rust replacement for [geographiclib](https://pypi.org/project/geographiclib/) and the distance functions of [geopy](https://pypi.org/project/geopy/). Same API, same results, 32–53x faster.

Replace `geopy` (or `geographiclib`) with `fastgeodesic` in the import. Nothing else changes.

```python
# before
from geopy.distance import geodesic
# after
from fastgeodesic.distance import geodesic

geodesic((35.3606, 138.7274), (35.6812, 139.7671)).meters
```

## Why

geographiclib is the standard library for accurate distances on the WGS84 ellipsoid, and geopy uses it under the hood. It is written in pure Python, so one distance takes about 40 µs. Loops over GPS logs, AIS tracks or all pairs of stations call it hundreds of thousands of times, which turns into minutes.

The usual advice is to switch to `pyproj.Geod` and rewrite the code to work on arrays. fastgeodesic is for when you would rather not rewrite: it runs the same algorithm (Karney 2013, via [geographiclib-rs](https://github.com/georust/geographiclib-rs)) in Rust and keeps the call-by-call API.

## Speed

Apple M1 Pro, Python 3.12, median of repeated runs.

| Workload | geographiclib / geopy | fastgeodesic | Speedup |
|---|---|---|---|
| `Geodesic.WGS84.Inverse`, 50,000 random pairs | 2,107 ms | 65 ms | 32x |
| `fastgeodesic.inverse_many`, same pairs | 2,107 ms | 33 ms | 64x |
| `geopy.distance.geodesic`, 20,000 random pairs | 1,195 ms | 23 ms | 53x |
| Total length of a 100,000-point GPS log with `geopy.distance.geodesic` | 3,597 ms | 82 ms | 44x |
| Same GPS log with `numpy.float64` coordinates (pandas rows) | 3,568 ms | 90 ms | 40x |

Short distances such as consecutive GPS points converge quickly even in pure Python, so the speedup there is smaller than for random pairs.

## Accuracy

Results match geographiclib to the last few bits. On 100,000 random pairs, 59% of `Inverse` results are bit-for-bit identical, and the largest difference is 7.5e-9 m in distance and 7.4e-13 degrees in azimuth. The test suite compares every output key against geographiclib, including poles, the antimeridian, near-antipodal points, `LONG_UNROLL` and a non-WGS84 ellipsoid. `fastgeodesic.distance` is tested against `geopy.distance` with floats, ints, lists, strings, `Point` objects, altitudes, `numpy.float64`, several points, other ellipsoids and `destination()`. Invalid input raises the same exception with the same message.

## Usage

The rule is always the same: replace the package name in the import.

| Before | After |
|---|---|
| `from geopy.distance import geodesic` | `from fastgeodesic.distance import geodesic` |
| `from geopy import distance` | `from fastgeodesic import distance` |
| `from geographiclib.geodesic import Geodesic` | `from fastgeodesic.geodesic import Geodesic` |

Only the files where you change the import are affected. geopy and geographiclib themselves are not modified, so other code in the same program keeps using them.

`fastgeodesic.distance.geodesic` is a subclass of `geopy.distance.geodesic`, so `.km`, `.miles`, `.destination()`, arithmetic, comparisons, `ellipsoid=` and `isinstance` checks work as before. The other names in `fastgeodesic.distance` (`great_circle`, `Distance`, `ELLIPSOIDS`, ...) are geopy's own objects.

`fastgeodesic.geodesic.Geodesic` has the same API as `geographiclib.geodesic.Geodesic`:

```python
from fastgeodesic.geodesic import Geodesic

r = Geodesic.WGS84.Inverse(35.3606, 138.7274, 35.6812, 139.7671)
r["s12"], r["azi1"], r["azi2"]

Geodesic.WGS84.Direct(35.3606, 138.7274, 45.0, 10_000, Geodesic.LATITUDE | Geodesic.LONGITUDE)
Geodesic(6377397.155, 1 / 299.1528128)  # any ellipsoid
```

For many pairs at once:

```python
import fastgeodesic
fastgeodesic.inverse_many(lat1, lon1, lat2, lon2)  # list of distances in meters, WGS84
```

### When you cannot change the import

If geopy is called inside a library you do not control, `patch()` makes geographiclib and geopy compute with fastgeodesic for the whole program:

```python
import fastgeodesic
fastgeodesic.patch()    # replaces Geodesic in geographiclib.geodesic and geopy.distance
...
fastgeodesic.unpatch()  # restores the originals
```

It replaces exactly one name, `Geodesic`, in those two modules. Call it before other modules copy the name with `from geographiclib.geodesic import Geodesic`. The speedup is smaller than changing the import (9x instead of 44x on GPS logs) because geopy's own Python code still runs.

## Supported API

| geographiclib | Status |
|---|---|
| `Geodesic(a, f)`, `Geodesic.WGS84`, `a`, `f`, all outmask constants | Supported |
| `Inverse(lat1, lon1, lat2, lon2, outmask)` | Supported |
| `Direct(lat1, lon1, azi1, s12, outmask)` | Supported |
| `ArcDirect`, `Line`, `InverseLine`, `DirectLine`, `Polygon` | Not yet |

| geopy.distance | Status |
|---|---|
| `geodesic`, `distance`, `GeodesicDistance`, including `ellipsoid=` | Supported, distances computed with fastgeodesic |
| `geodesic(...).destination()` | Supported, computed by geopy itself |
| `great_circle`, `Distance`, `ELLIPSOIDS` and the rest | geopy's own objects, passed through |


## Install

```sh
pip install fastgeodesic
```

Prebuilt wheels for Linux, macOS and Windows on x86_64 and ARM, Python 3.9 and later. `fastgeodesic.distance` needs geopy 2.x, which you already have if you are replacing geopy imports; `pip install "fastgeodesic[geopy]"` installs it too. It is tested with geopy 2.0 to 2.5. On other geopy versions distances are still computed with fastgeodesic, but object construction falls back to geopy's own code, so it is slower.

To build from source you need a Rust toolchain:

```sh
pip install maturin
maturin develop --release
```

## License

MIT. Uses [geographiclib-rs](https://github.com/georust/geographiclib-rs) (MIT), a port of Charles Karney's [GeographicLib](https://geographiclib.sourceforge.io/).
