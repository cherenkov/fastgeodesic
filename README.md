# fastgeodesic

Drop-in Rust replacement for [geographiclib](https://pypi.org/project/geographiclib/) and the distance functions of [geopy](https://pypi.org/project/geopy/). Same API, same results, 9–32x faster. Your existing code does not change.

```python
import fastgeodesic
fastgeodesic.patch()  # add this one line

# existing code, unchanged
from geopy.distance import geodesic
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
| `geopy.distance.geodesic`, 20,000 random pairs | 1,224 ms | 87 ms | 14x |
| Total length of a 100,000-point GPS log with geopy | 3,718 ms | 407 ms | 9.1x |

Short distances such as consecutive GPS points converge quickly even in pure Python, so the speedup there is smaller than for random pairs.

## Accuracy

Results match geographiclib to the last few bits. On 100,000 random pairs, 59% of `Inverse` results are bit-for-bit identical, and the largest difference is 7.5e-9 m in distance and 7.4e-13 degrees in azimuth. The test suite compares every output key against geographiclib, including poles, the antimeridian, near-antipodal points, `LONG_UNROLL` and a non-WGS84 ellipsoid.

## Usage

Patch geographiclib and geopy in place. Code that imports them, including other libraries, uses fastgeodesic from then on.

```python
import fastgeodesic
fastgeodesic.patch()
...
fastgeodesic.unpatch()  # back to the originals
```

Or import it directly, with the same API as `geographiclib.geodesic`:

```python
from fastgeodesic.geodesic import Geodesic

r = Geodesic.WGS84.Inverse(35.3606, 138.7274, 35.6812, 139.7671)
r["s12"], r["azi1"], r["azi2"]

Geodesic.WGS84.Direct(35.3606, 138.7274, 45.0, 10_000, Geodesic.LATITUDE | Geodesic.LONGITUDE)
Geodesic(6377397.155, 1 / 299.1528128)  # any ellipsoid
```

For many pairs at once:

```python
fastgeodesic.inverse_many(lat1, lon1, lat2, lon2)  # list of distances in meters, WGS84
```

## Supported API

| geographiclib | Status |
|---|---|
| `Geodesic(a, f)`, `Geodesic.WGS84`, `a`, `f`, all outmask constants | Supported |
| `Inverse(lat1, lon1, lat2, lon2, outmask)` | Supported |
| `Direct(lat1, lon1, azi1, s12, outmask)` | Supported |
| `ArcDirect`, `Line`, `InverseLine`, `DirectLine`, `Polygon` | Not yet |

`patch()` replaces `Geodesic` in `geographiclib.geodesic` and `geopy.distance`. Call it before other modules copy the name with `from geographiclib.geodesic import Geodesic`.

## Install

Not on PyPI yet. To build from source you need a Rust toolchain:

```sh
pip install maturin
maturin develop --release
```

## License

MIT. Uses [geographiclib-rs](https://github.com/georust/geographiclib-rs) (MIT), a port of Charles Karney's [GeographicLib](https://geographiclib.sourceforge.io/).
