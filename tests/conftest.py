import os

# Number of random samples per test, scaled by FASTGEODESIC_TEST_SCALE.
# CI sets a small scale on emulated CPUs, where pure-Python geographiclib is very slow.
SCALE = float(os.environ.get("FASTGEODESIC_TEST_SCALE", "1"))


def samples(n):
    return max(100, int(n * SCALE))
