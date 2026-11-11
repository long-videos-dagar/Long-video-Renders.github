import math
T0 = [0.0]
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def K(keys):
    keys = sorted(keys, key=lambda k: k[0])
    def f(t):
        if t <= keys[0][0]: return keys[0][1]
        if t >= keys[-1][0]: return keys[-1][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = ease((t - t0) / max(1e-6, t1 - t0))
                if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * u
    return f
def LK(keys):
    keys = sorted(keys, key=lambda k: k[0])
    def f(t):
        if t <= keys[0][0]: return keys[0][1]
        if t >= keys[-1][0]: return keys[-1][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / max(1e-6, t1 - t0)
                if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * u
    return f
