"""Offscreen smoke test: the widgets build and paint in every language."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from tofu_eq import i18n  # noqa: E402
from tofu_eq.band_panel import BandPanel  # noqa: E402
from tofu_eq.curve_widget import CurveWidget  # noqa: E402
from tofu_eq.model import default_state  # noqa: E402

app = QApplication.instance() or QApplication([])


class TestWidgets(unittest.TestCase):
    def test_paint_all_languages(self):
        for lang in i18n.LANGUAGES:
            with self.subTest(lang=lang):
                i18n.set_language(lang)
                st = default_state()
                curve = CurveWidget()
                curve.resize(800, 360)
                curve.set_state(st, 48000)
                curve.set_selected(2)
                self.assertFalse(curve.grab().isNull())
                panel = BandPanel()
                panel.set_state(st, 48000, 2)
                self.assertEqual(len(panel.rows), len(st.bands))
        i18n.set_language("en")

    def test_spectrum_overlay(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        curve = CurveWidget()
        curve.resize(800, 360)
        curve.set_state(default_state(), 48000)
        curve.set_spectrum(np.linspace(-20, -90, 300))
        self.assertFalse(curve.grab().isNull())


if __name__ == "__main__":
    unittest.main()
