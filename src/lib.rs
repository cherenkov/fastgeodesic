use geographiclib_rs::{capability as caps, Geodesic as G};
use pyo3::prelude::*;
use pyo3::intern;
use pyo3::types::PyDict;

// Same results as Math.AngNormalize, LatFix and AngDiff in geographiclib (Python).
// Copied because geomath is private in geographiclib-rs.
fn ang_normalize(x: f64) -> f64 {
    let mut y = x % 360.0;
    if y > 180.0 {
        y -= 360.0;
    } else if y < -180.0 {
        y += 360.0;
    }
    if y == -180.0 {
        180.0
    } else {
        y
    }
}

fn lat_fix(x: f64) -> f64 {
    if x.abs() > 90.0 {
        f64::NAN
    } else {
        x
    }
}

fn two_sum(u: f64, v: f64) -> (f64, f64) {
    let s = u + v;
    let up = s - v;
    let vpp = s - up;
    let t = -((up - u) + (vpp - v));
    (s, t)
}

fn ang_diff(x: f64, y: f64) -> (f64, f64) {
    let (d, t) = two_sum(ang_normalize(-x), ang_normalize(y));
    let d = ang_normalize(d);
    if d == 180.0 && t > 0.0 {
        two_sum(-180.0, t)
    } else {
        two_sum(d, t)
    }
}

fn atan2d(y: f64, x: f64) -> f64 {
    // Same quadrant handling as atan2d in geographiclib
    let (mut y, mut x) = (y, x);
    let mut q = 0;
    if y.abs() > x.abs() {
        std::mem::swap(&mut x, &mut y);
        q = 2;
    }
    if x.is_sign_negative() {
        x = -x;
        q += 1;
    }
    let mut ang = y.atan2(x).to_degrees();
    match q {
        1 => ang = 180.0_f64.copysign(y) - ang,
        2 => ang = 90.0 - ang,
        3 => ang = -90.0 + ang,
        _ => {}
    }
    ang
}

#[pyclass(subclass, module = "fastgeodesic._core")]
pub struct Geodesic {
    g: G,
    #[pyo3(get)]
    a: f64,
    #[pyo3(get)]
    f: f64,
}

#[pymethods]
impl Geodesic {
    #[new]
    fn new(a: f64, f: f64) -> Self {
        Geodesic { g: G::new(a, f), a, f }
    }

    #[pyo3(name = "Inverse", signature = (lat1, lon1, lat2, lon2, outmask = caps::STANDARD))]
    fn inverse<'py>(
        &self,
        py: Python<'py>,
        lat1: f64,
        lon1: f64,
        lat2: f64,
        lon2: f64,
        outmask: u64,
    ) -> PyResult<Bound<'py, PyDict>> {
        let (a12, s12, salp1, calp1, salp2, calp2, m12, mm12, mm21, ss12) =
            self.g._gen_inverse(lat1, lon1, lat2, lon2, outmask);
        let outmask = outmask & caps::OUT_MASK;
        let unroll = outmask & caps::LONG_UNROLL != 0;
        let lon2o = if unroll {
            let (lon12, e) = ang_diff(lon1, lon2);
            (lon1 + lon12) + e
        } else {
            ang_normalize(lon2)
        };
        let d = PyDict::new(py);
        d.set_item(intern!(py, "lat1"), lat_fix(lat1))?;
        d.set_item(intern!(py, "lon1"), if unroll { lon1 } else { ang_normalize(lon1) })?;
        d.set_item(intern!(py, "lat2"), lat_fix(lat2))?;
        d.set_item(intern!(py, "lon2"), lon2o)?;
        d.set_item(intern!(py, "a12"), a12)?;
        if outmask & caps::DISTANCE & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "s12"), s12)?;
        }
        if outmask & caps::AZIMUTH & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "azi1"), atan2d(salp1, calp1))?;
            d.set_item(intern!(py, "azi2"), atan2d(salp2, calp2))?;
        }
        if outmask & caps::REDUCEDLENGTH & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "m12"), m12)?;
        }
        if outmask & caps::GEODESICSCALE & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "M12"), mm12)?;
            d.set_item(intern!(py, "M21"), mm21)?;
        }
        if outmask & caps::AREA & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "S12"), ss12)?;
        }
        Ok(d)
    }

    #[pyo3(name = "Direct", signature = (lat1, lon1, azi1, s12, outmask = caps::STANDARD))]
    fn direct<'py>(
        &self,
        py: Python<'py>,
        lat1: f64,
        lon1: f64,
        azi1: f64,
        s12: f64,
        outmask: u64,
    ) -> PyResult<Bound<'py, PyDict>> {
        let (a12, lat2, lon2, azi2, s12o, m12, mm12, mm21, ss12) =
            self.g._gen_direct(lat1, lon1, azi1, false, s12, outmask);
        let outmask = outmask & caps::OUT_MASK;
        let unroll = outmask & caps::LONG_UNROLL != 0;
        let d = PyDict::new(py);
        d.set_item(intern!(py, "lat1"), lat_fix(lat1))?;
        d.set_item(intern!(py, "lon1"), if unroll { lon1 } else { ang_normalize(lon1) })?;
        d.set_item(intern!(py, "azi1"), ang_normalize(azi1))?;
        d.set_item(intern!(py, "s12"), s12o)?;
        d.set_item(intern!(py, "a12"), a12)?;
        if outmask & caps::LATITUDE & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "lat2"), lat2)?;
        }
        if outmask & caps::LONGITUDE & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "lon2"), lon2)?;
        }
        if outmask & caps::AZIMUTH & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "azi2"), azi2)?;
        }
        if outmask & caps::REDUCEDLENGTH & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "m12"), m12)?;
        }
        if outmask & caps::GEODESICSCALE & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "M12"), mm12)?;
            d.set_item(intern!(py, "M21"), mm21)?;
        }
        if outmask & caps::AREA & caps::OUT_MASK != 0 {
            d.set_item(intern!(py, "S12"), ss12)?;
        }
        Ok(d)
    }

    /// Internal: distance only, without building a dict
    fn _s12(&self, lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
        self.g._gen_inverse(lat1, lon1, lat2, lon2, caps::DISTANCE).1
    }

    /// Not in geographiclib: distances in meters for many pairs at once
    fn inverse_many(
        &self,
        py: Python<'_>,
        lat1: Vec<f64>,
        lon1: Vec<f64>,
        lat2: Vec<f64>,
        lon2: Vec<f64>,
    ) -> PyResult<Vec<f64>> {
        let n = lat1.len();
        if lon1.len() != n || lat2.len() != n || lon2.len() != n {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "lat1, lon1, lat2, lon2 must have the same length",
            ));
        }
        Ok(py.allow_threads(|| {
            (0..n)
                .map(|i| self.g._gen_inverse(lat1[i], lon1[i], lat2[i], lon2[i], caps::DISTANCE).1)
                .collect()
        }))
    }
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Geodesic>()?;
    m.add("WGS84_A", 6378137.0)?;
    m.add("WGS84_F", 1.0 / 298.257223563)?;
    Ok(())
}
