import unittest

from tofu_eq import backend, dsp
from tofu_eq.model import Band, EqState, default_state


class TestConfig(unittest.TestCase):
    def test_slots(self):
        self.assertEqual(backend.slots_for(0), 8)
        self.assertEqual(backend.slots_for(8), 8)
        self.assertEqual(backend.slots_for(9), 16)

    def test_conf_has_every_slot_and_rate(self):
        st = default_state()
        conf = backend.build_conf(st, 16)
        self.assertEqual(conf.count("label = bq_raw"), 16)
        for rate in backend.RATES:
            self.assertEqual(conf.count(f"rate = {rate} "), 16)
        self.assertIn('outputs = [ "s16:Out" ]', conf)
        self.assertIn("filter.smart      = true", conf)
        self.assertEqual(conf.count("{"), conf.count("}"))

    def test_disabled_and_bypass_are_identity(self):
        st = EqState(preamp=-6.0, bands=[Band("peak", 1000, 6, 1), Band("peak", 200, 3, 1, enabled=False)])
        cf = backend.slot_coeffs(st, 8, 48000)
        self.assertNotEqual(cf[0], dsp.IDENTITY)
        self.assertEqual(cf[1:], [dsp.IDENTITY] * 7)
        self.assertAlmostEqual(backend.preamp_mult(st), 10 ** (-6 / 20))
        st.bypass = True
        self.assertEqual(backend.slot_coeffs(st, 8, 48000), [dsp.IDENTITY] * 8)
        self.assertEqual(backend.preamp_mult(st), 1.0)

    def test_state_roundtrip(self):
        st = default_state()
        self.assertEqual(EqState.from_dict(st.to_dict()), st)


if __name__ == "__main__":
    unittest.main()
