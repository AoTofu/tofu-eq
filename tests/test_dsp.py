import unittest

from tofu_eq import dsp

RATE = 48000


def mag(kind, f, freq=1000.0, gain=6.0, q=0.7071, rate=RATE):
    return dsp.magnitude_db(dsp.coeffs(kind, freq, gain, q, rate), f, rate)


class TestBiquads(unittest.TestCase):
    def test_peak_hits_gain_at_center(self):
        for gain in (-12.0, -3.0, 3.0, 12.0):
            self.assertAlmostEqual(mag("peak", 1000, gain=gain, q=1.41), gain, places=6)

    def test_peak_is_flat_far_away(self):
        self.assertAlmostEqual(mag("peak", 20, gain=12, q=4), 0.0, places=1)

    def test_shelves(self):
        self.assertAlmostEqual(mag("lowshelf", 10), 6.0, places=1)
        self.assertAlmostEqual(mag("lowshelf", 20000), 0.0, places=1)
        self.assertAlmostEqual(mag("highshelf", 20000), 6.0, places=1)
        self.assertAlmostEqual(mag("highshelf", 10), 0.0, places=1)
        self.assertAlmostEqual(mag("lowshelf", 1000), 3.0, places=2)  # midpoint

    def test_butterworth_cutoff_is_minus_3db(self):
        self.assertAlmostEqual(mag("lowpass", 1000), -3.01, places=2)
        self.assertAlmostEqual(mag("highpass", 1000), -3.01, places=2)

    def test_notch_allpass_bandpass(self):
        self.assertLess(mag("notch", 1000), -60)
        self.assertAlmostEqual(mag("allpass", 300), 0.0, places=6)
        self.assertAlmostEqual(mag("bandpass", 1000), 0.0, places=6)

    def test_normalized_and_clamped(self):
        for kind in dsp.TYPES:
            cf = dsp.coeffs(kind, 30000.0, 3.0, 0.0, 44100)  # above Nyquist, Q=0 -> clamped
            self.assertEqual(cf[3], 1.0)
            self.assertTrue(all(abs(c) < 1e6 for c in cf))

    def test_identity(self):
        self.assertAlmostEqual(dsp.magnitude_db(dsp.IDENTITY, 1234, RATE), 0.0)


if __name__ == "__main__":
    unittest.main()
