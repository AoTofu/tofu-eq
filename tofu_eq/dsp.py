"""Biquad coefficients (RBJ Audio EQ Cookbook) and frequency response, in pure Python."""
import cmath
import math

TYPES = ["peak", "lowshelf", "highshelf", "lowpass", "highpass", "bandpass", "notch", "allpass"]
LABELS = {
    "peak": "Peak",
    "lowshelf": "Low shelf",
    "highshelf": "High shelf",
    "lowpass": "Low-pass",
    "highpass": "High-pass",
    "bandpass": "Band-pass",
    "notch": "Notch",
    "allpass": "All-pass",
}
GAIN_TYPES = {"peak", "lowshelf", "highshelf"}
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def coeffs(kind, freq, gain, q, rate):
    """Return (b0, b1, b2, a0, a1, a2) normalized so that a0 == 1."""
    freq = min(max(freq, 1.0), rate * 0.4975)
    q = max(q, 0.01)
    A = 10.0 ** (gain / 40.0)
    w0 = 2.0 * math.pi * freq / rate
    c, s = math.cos(w0), math.sin(w0)
    alpha = s / (2.0 * q)

    if kind == "peak":
        b = (1 + alpha * A, -2 * c, 1 - alpha * A)
        a = (1 + alpha / A, -2 * c, 1 - alpha / A)
    elif kind in ("lowshelf", "highshelf"):
        sa = 2.0 * math.sqrt(A) * alpha
        if kind == "lowshelf":
            b = (A * ((A + 1) - (A - 1) * c + sa), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sa))
            a = ((A + 1) + (A - 1) * c + sa, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sa)
        else:
            b = (A * ((A + 1) + (A - 1) * c + sa), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sa))
            a = ((A + 1) - (A - 1) * c + sa, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sa)
    elif kind == "lowpass":
        b = ((1 - c) / 2, 1 - c, (1 - c) / 2)
        a = (1 + alpha, -2 * c, 1 - alpha)
    elif kind == "highpass":
        b = ((1 + c) / 2, -(1 + c), (1 + c) / 2)
        a = (1 + alpha, -2 * c, 1 - alpha)
    elif kind == "bandpass":
        b = (alpha, 0.0, -alpha)
        a = (1 + alpha, -2 * c, 1 - alpha)
    elif kind == "notch":
        b = (1.0, -2 * c, 1.0)
        a = (1 + alpha, -2 * c, 1 - alpha)
    elif kind == "allpass":
        b = (1 - alpha, -2 * c, 1 + alpha)
        a = (1 + alpha, -2 * c, 1 - alpha)
    else:
        return IDENTITY
    a0 = a[0]
    return (b[0] / a0, b[1] / a0, b[2] / a0, 1.0, a[1] / a0, a[2] / a0)


def magnitude_db(cf, freq, rate):
    b0, b1, b2, _, a1, a2 = cf
    z = cmath.exp(-2j * math.pi * freq / rate)
    h = (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20.0 * math.log10(max(abs(h), 1e-9))


def log_freqs(n=300, lo=20.0, hi=20000.0):
    r = math.log(hi / lo)
    return [lo * math.exp(r * i / (n - 1)) for i in range(n)]
