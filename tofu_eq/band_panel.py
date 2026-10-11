"""Band list: on/off, type, frequency, gain and Q for every band."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QLabel,
                               QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from . import dsp
from .curve_widget import band_color
from .i18n import tr


def _spin(lo, hi, dec, suffix):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSuffix(suffix)
    s.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
    s.setKeyboardTracking(False)
    s.setAccelerated(True)
    return s


class BandRow:
    def __init__(self, panel, i):
        self.num = QToolButton(text=str(i + 1), checkable=True, autoRaise=True)
        c = band_color(i).name()
        self.num.setStyleSheet(f"QToolButton {{ color: {c}; font-weight: bold; min-width: 26px; }}"
                               f"QToolButton:checked {{ background: {c}; color: white; border-radius: 4px; }}")
        self.enabled = QCheckBox()
        self.type = QComboBox()
        for t in dsp.TYPES:
            self.type.addItem(tr(dsp.LABELS[t]), t)
        self.freq = _spin(10.0, 24000.0, 1, " Hz")
        self.gain = _spin(-30.0, 30.0, 1, " dB")
        self.gain.setSingleStep(0.5)
        self.q = _spin(0.05, 30.0, 3, "")
        self.remove = QToolButton(text="✕", autoRaise=True, toolTip=tr("Remove this band"))
        self.widgets = [self.num, self.enabled, self.type, self.freq, self.gain, self.q, self.remove]

        self.num.clicked.connect(lambda: panel.bandSelected.emit(i))
        self.enabled.toggled.connect(lambda v: panel.edit(i, {"enabled": v}))
        self.type.currentIndexChanged.connect(lambda _: panel.edit(i, {"type": self.type.currentData()}))
        self.freq.valueChanged.connect(lambda v: panel.edit(i, {"freq": v}))
        self.gain.valueChanged.connect(lambda v: panel.edit(i, {"gain": v}))
        self.q.valueChanged.connect(lambda v: panel.edit(i, {"q": v}))
        self.remove.clicked.connect(lambda: panel.removeRequested.emit(i))

    def load(self, b, nyquist):
        for w in self.widgets:
            w.blockSignals(True)
        self.enabled.setChecked(b.enabled)
        self.type.setCurrentIndex(dsp.TYPES.index(b.type) if b.type in dsp.TYPES else 0)
        self.freq.setMaximum(min(24000.0, nyquist * 0.99))
        self.freq.setValue(b.freq)
        self.gain.setValue(b.gain)
        self.gain.setEnabled(b.type in dsp.GAIN_TYPES)
        self.q.setValue(b.q)
        for w in self.widgets:
            w.blockSignals(False)


class BandPanel(QWidget):
    bandEdited = Signal(int, dict)
    bandSelected = Signal(int)
    removeRequested = Signal(int)
    addRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self._loading = False
        inner = QWidget()
        self.grid = QGridLayout(inner)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setHorizontalSpacing(10)
        for col, text in enumerate(["#", tr("On"), tr("Type"), tr("Frequency"), tr("Gain"), "Q", ""]):
            lab = QLabel(text)
            lab.setStyleSheet("color: palette(mid); font-weight: bold;")
            self.grid.addWidget(lab, 0, col)
        self.grid.setColumnStretch(7, 1)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(inner)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.add_btn = QPushButton(tr("+ Add band"))
        self.add_btn.clicked.connect(self.addRequested)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        lay.addWidget(self.add_btn, 0, Qt.AlignLeft)
        self._inner = inner

    def edit(self, i, change):
        if not self._loading:
            self.bandSelected.emit(i)
            self.bandEdited.emit(i, change)

    def set_state(self, state, rate, selected):
        self._loading = True
        n = len(state.bands)
        while len(self.rows) > n:
            for w in self.rows.pop().widgets:
                w.deleteLater()
        while len(self.rows) < n:
            i = len(self.rows)
            row = BandRow(self, i)
            for col, w in enumerate(row.widgets):
                self.grid.addWidget(w, i + 1, col)
            self.rows.append(row)
        for r in range(self.grid.rowCount()):
            self.grid.setRowStretch(r, 1 if r == n + 1 else 0)
        for i, (row, b) in enumerate(zip(self.rows, state.bands)):
            row.load(b, rate / 2)
            row.num.setChecked(i == selected)
        self._loading = False
