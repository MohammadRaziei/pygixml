"""
timing.py: the one timing statistic every benchmark here uses.

A benchmark runs the operation `repeats` times (DEFAULT_REPEATS = 10) and
reports the TRIMMED MEAN: sort the samples, drop the fastest and the slowest
tenth, average the rest. With 10 repeats that is the mean of the middle 8.

Why not the minimum: the minimum is one lucky run, so it moves with the
noise it is trying to avoid, and it flatters whichever library happened to
get the quiet moment. Why not the plain mean: one run interrupted by another
process drags it up. The trimmed mean keeps the typical run and drops both
tails. (With fewer than 10 repeats nothing is trimmed and it is a plain mean.)
"""
import gc
import time

DEFAULT_REPEATS = 10
TRIM = 0.1
METRIC = "trimmed mean wall-clock seconds over repeats (fastest and slowest tenth dropped)"


def trimmed_mean(samples, trim=TRIM):
    s = sorted(samples)
    k = int(len(s) * trim)
    core = s[k:len(s) - k] or s
    return sum(core) / len(core)


def timed(fn, repeats=DEFAULT_REPEATS):
    """Call fn() `repeats` times (gc.collect() before each) and return the trimmed mean in seconds."""
    samples = []
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return trimmed_mean(samples)
