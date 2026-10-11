"""Main window: owns the EQ state and wires the widgets to the backend."""
from PySide6.QtCore import QEvent, QSettings, Qt, QTimer
from PySide6.QtGui import QActionGroup, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QInputDialog, QLabel, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QSlider, QSplitter, QToolButton, QVBoxLayout,
                               QWidget)

from . import i18n, model
from .backend import Backend
from .band_panel import BandPanel
from .curve_widget import CurveWidget
from .i18n import tr
from .spectrum import HAVE_NUMPY, SpectrumAnalyzer

MAX_BANDS = 32


class MainWindow(QMainWindow):
    def __init__(self, relaunch=None):
        super().__init__()
        self._relaunch = relaunch  # callable(geometry) that opens a fresh window (used to switch language)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Tofu EQ")
        self.setWindowIcon(QIcon.fromTheme("tofu-eq", QIcon.fromTheme("view-media-equalizer")))
        self.resize(980, 760)
        self.state = model.load_state()
        self.selected = 0 if self.state.bands else -1

        self.backend = Backend(self)
        self.backend.status.connect(lambda s: self.statusBar().showMessage(s))
        self.backend.rateChanged.connect(lambda _: self._refresh_views())

        # --- top bar ---
        self.preset = QComboBox(minimumWidth=180)
        self.preset.setPlaceholderText(tr("Presets"))
        self.preset.activated.connect(self._load_preset)
        save_btn = QPushButton(tr("Save…"))
        save_btn.clicked.connect(self._save_preset)
        del_btn = QPushButton(tr("Delete"))
        del_btn.clicked.connect(self._delete_preset)
        reset_btn = QPushButton(tr("Flat"))
        reset_btn.setToolTip(tr("Reset all band gains and the preamp to 0 dB"))
        reset_btn.clicked.connect(self._flatten)

        self.pre_slider = QSlider(Qt.Horizontal, minimum=-300, maximum=120, minimumWidth=140)
        self.pre_spin = QDoubleSpinBox(minimum=-30.0, maximum=12.0, decimals=1, singleStep=0.5, suffix=" dB")
        self.pre_spin.setKeyboardTracking(False)
        self.pre_slider.valueChanged.connect(lambda v: self._set_preamp(v / 10.0))
        self.pre_spin.valueChanged.connect(self._set_preamp)
        self.auto_btn = QPushButton(tr("Auto"))
        self.auto_btn.setToolTip(tr("Set the preamp to offset the EQ's maximum boost so the output can't clip"))
        self.auto_btn.clicked.connect(self._auto_preamp)
        self.clip_label = QLabel()

        self.bypass_btn = QPushButton(tr("Bypass"), checkable=True)
        self.bypass_btn.setToolTip(tr("Temporarily disable the EQ (Ctrl+B)"))
        self.bypass_btn.toggled.connect(self._set_bypass)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self.bypass_btn.toggle)

        self.settings = QSettings("tofu-eq", "tofu-eq")
        self.analyzer = SpectrumAnalyzer(self)
        self.spec_btn = QPushButton(tr("Spectrum"), checkable=True)
        if HAVE_NUMPY:
            self.spec_btn.setToolTip(tr("Show the post-EQ spectrum behind the curve (captured only while this window is visible)"))
            self.spec_btn.setChecked(self.settings.value("spectrum", True, type=bool))
        else:
            self.spec_btn.setEnabled(False)
            self.spec_btn.setToolTip(tr("Requires numpy (install the python3-numpy package)"))
        self.spec_btn.toggled.connect(self._spectrum_toggled)

        lang_btn = QToolButton(popupMode=QToolButton.InstantPopup, autoRaise=True, toolTip=tr("Language"))
        lang_btn.setText(i18n.LANGUAGES[i18n.current()])
        lang_menu = QMenu(lang_btn)
        group = QActionGroup(lang_menu)
        saved = self.settings.value("language", "auto")
        for code, label in [("auto", tr("System default"))] + list(i18n.LANGUAGES.items()):
            act = lang_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(code == saved)
            group.addAction(act)
            act.triggered.connect(lambda _=False, code=code: self._set_language(code))
        lang_btn.setMenu(lang_menu)

        top = QHBoxLayout()
        top.addWidget(self.preset)
        top.addWidget(save_btn)
        top.addWidget(del_btn)
        top.addWidget(reset_btn)
        top.addSpacing(16)
        top.addWidget(QLabel(tr("Preamp")))
        top.addWidget(self.pre_slider)
        top.addWidget(self.pre_spin)
        top.addWidget(self.auto_btn)
        top.addWidget(self.clip_label)
        top.addStretch(1)
        top.addWidget(self.spec_btn)
        top.addWidget(self.bypass_btn)
        top.addWidget(lang_btn)

        # --- curve + bands ---
        self.curve = CurveWidget()
        self.curve.bandEdited.connect(self._edit_band)
        self.curve.bandSelected.connect(self._select)
        self.curve.addRequested.connect(lambda f, g: self._add_band(f, g))
        self.curve.removeRequested.connect(self._remove_band)
        self.curve.typeRequested.connect(lambda i, t: self._edit_band(i, {"type": t}))
        self.curve.toggleRequested.connect(lambda i: self._edit_band(i, {"enabled": not self.state.bands[i].enabled}))
        hint = QLabel(tr("Drag: frequency/gain    Wheel: Q    Double-click: add band    Right-click: type/delete"))
        hint.setStyleSheet("color: palette(mid);")

        self.panel = BandPanel()
        self.panel.bandEdited.connect(self._edit_band)
        self.panel.bandSelected.connect(self._select)
        self.panel.removeRequested.connect(self._remove_band)
        self.panel.addRequested.connect(lambda: self._add_band(1000.0, 0.0))

        upper = QWidget()
        ul = QVBoxLayout(upper)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.addWidget(self.curve, 1)
        ul.addWidget(hint)
        split = QSplitter(Qt.Vertical)
        split.addWidget(upper)
        split.addWidget(self.panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        split.setSizes([400, 300])

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(top)
        lay.addWidget(split, 1)
        self.setCentralWidget(central)

        self._save_timer = QTimer(self, singleShot=True, interval=1000)
        self._save_timer.timeout.connect(lambda: model.save_state(self.state))

        self._reload_presets()
        self._refresh_views()
        self.backend.start(self.state)
        self.analyzer.frame.connect(self.curve.set_spectrum)
        self.backend.deviceChanged.connect(self.analyzer.set_device)
        self.analyzer.set_device(self.backend.device)
        self._update_spectrum()

    # --- view sync ------------------------------------------------------
    def _refresh_views(self):
        rate = self.backend.rate
        self.curve.set_state(self.state, rate)
        self.curve.set_selected(self.selected)
        self.panel.set_state(self.state, rate, self.selected)
        self.panel.add_btn.setEnabled(len(self.state.bands) < MAX_BANDS)
        for w in (self.pre_slider, self.pre_spin, self.bypass_btn):
            w.blockSignals(True)
        self.pre_slider.setValue(round(self.state.preamp * 10))
        self.pre_spin.setValue(self.state.preamp)
        self.bypass_btn.setChecked(self.state.bypass)
        for w in (self.pre_slider, self.pre_spin, self.bypass_btn):
            w.blockSignals(False)
        headroom = self.curve.eq_peak_db() + self.state.preamp
        if headroom > 0.05 and not self.state.bypass:
            self.clip_label.setText(tr("⚠ +{db} dB may clip", db=f"{headroom:.1f}"))
            self.clip_label.setStyleSheet("color: #e8615a;")
        else:
            self.clip_label.setText("")

    def _changed(self):
        self._refresh_views()
        self.backend.apply(self.state)
        self._save_timer.start()

    # --- edits ----------------------------------------------------------
    def _select(self, i):
        if i != self.selected:
            self.selected = i
            self.curve.set_selected(i)
            for k, row in enumerate(self.panel.rows):
                row.num.setChecked(k == i)

    def _edit_band(self, i, change):
        if 0 <= i < len(self.state.bands):
            b = self.state.bands[i]
            for k, v in change.items():
                setattr(b, k, v)
            self._changed()

    def _add_band(self, freq, gain):
        if len(self.state.bands) >= MAX_BANDS:
            return
        self.state.bands.append(model.Band("peak", freq, gain, 1.41))
        self.selected = len(self.state.bands) - 1
        self._changed()

    def _remove_band(self, i):
        if 0 <= i < len(self.state.bands):
            del self.state.bands[i]
            self.selected = min(self.selected, len(self.state.bands) - 1)
            self._changed()

    def _set_preamp(self, db):
        self.state.preamp = round(db, 1)
        self._changed()

    def _auto_preamp(self):
        self._set_preamp(-max(0.0, self.curve.eq_peak_db()))

    def _set_bypass(self, on):
        self.state.bypass = on
        self._changed()

    def _flatten(self):
        for b in self.state.bands:
            b.gain = 0.0
        self.state.preamp = 0.0
        self._changed()

    # --- presets --------------------------------------------------------
    def _reload_presets(self, current=None):
        self.preset.clear()
        self.preset.addItems(model.list_presets())
        self.preset.setCurrentIndex(self.preset.findText(current) if current else -1)

    def _load_preset(self, idx):
        name = self.preset.itemText(idx)
        try:
            st = model.load_preset(name)
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.warning(self, "Tofu EQ", tr("Failed to load preset: {err}", err=e))
            return
        st.bypass = self.state.bypass
        self.state = st
        self.selected = 0 if st.bands else -1
        self._changed()

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, tr("Save preset"), tr("Name:"), text=self.preset.currentText())
        name = name.strip().replace("/", "_")
        if ok and name:
            model.save_preset(name, self.state)
            self._reload_presets(name)

    def _delete_preset(self):
        name = self.preset.currentText()
        if name and QMessageBox.question(self, "Tofu EQ", tr("Delete preset “{name}”?", name=name)) == QMessageBox.Yes:
            model.delete_preset(name)
            self._reload_presets()

    # --- language -------------------------------------------------------
    def _set_language(self, code):
        """Save the choice and swap in a freshly built window (all widgets re-translated)."""
        self.settings.setValue("language", code)
        new = i18n.resolve(None if code == "auto" else code)
        if new == i18n.current() or self._relaunch is None:
            return
        i18n.set_language(new)
        geometry = self.saveGeometry()
        model.save_state(self.state)
        self._relaunch(geometry)  # open the new window before closing this one so the app keeps running
        self.close()

    # --- spectrum: capture only while the window is actually visible ----------
    # Wayland never tells a client it was minimized, so use the QWindow "exposed" state.
    def _update_spectrum(self):
        win = self.windowHandle()
        exposed = win is not None and win.isExposed()
        if self.spec_btn.isChecked() and self.isVisible() and not self.isMinimized() and exposed:
            self.analyzer.start()
        else:
            self.analyzer.stop()

    def eventFilter(self, obj, ev):
        if obj is self.windowHandle() and ev.type() == QEvent.Expose:
            QTimer.singleShot(0, self._update_spectrum)
        return super().eventFilter(obj, ev)

    def _spectrum_toggled(self, on):
        self.settings.setValue("spectrum", on)
        self._update_spectrum()

    def showEvent(self, ev):
        super().showEvent(ev)
        if self.windowHandle() is not None:
            self.windowHandle().installEventFilter(self)  # Qt ignores duplicate installs
        self._update_spectrum()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._update_spectrum()

    def changeEvent(self, ev):
        super().changeEvent(ev)
        if ev.type() == QEvent.WindowStateChange:
            self._update_spectrum()

    def closeEvent(self, ev):
        self.analyzer.stop()
        model.save_state(self.state)
        self.backend._write_conf()
        super().closeEvent(ev)
