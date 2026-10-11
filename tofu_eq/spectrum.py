"""Spectrum of the post-EQ sound, captured with pw-record only while the GUI is visible.

WirePlumber redirects even sink-monitor captures to the smart filter (i.e. the EQ's
*input*), so pw-record starts unlinked and we pw-link it to the monitor of the
device the EQ outputs to.
"""
import subprocess

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from . import dsp

try:
    import numpy as np
except ImportError:
    np = None

HAVE_NUMPY = np is not None
RATE = 48000
FFT_N = 8192
FPS = 30
FLOOR_DB = -100.0
FALL_DB = 1.2  # decay per frame


class SpectrumAnalyzer(QObject):
    frame = Signal(object)  # dBFS per dsp.log_freqs() point (1/12-octave band power)

    def __init__(self, parent=None, device=""):
        super().__init__(parent)
        self.device = device  # node.name of the sink whose monitor we capture
        self._running = False
        self._proc = None
        self._link_tries = 0
        self._link_timer = QTimer(self, interval=250)
        self._link_timer.timeout.connect(self._link)
        self._rest = b""
        self._fresh = False
        self._timer = QTimer(self, interval=1000 // FPS)
        self._timer.timeout.connect(self._tick)
        if HAVE_NUMPY:
            self._setup_bins()

    def _setup_bins(self):
        self._buf = np.zeros(FFT_N, dtype=np.float32)
        self._win = np.hanning(FFT_N).astype(np.float32)
        self._norm = 2.0 / (FFT_N * float(np.sum(self._win.astype(np.float64) ** 2)))
        freqs = np.array(dsp.log_freqs())
        df = RATE / FFT_N
        half = 2.0 ** (1.0 / 24.0)
        self._lo = np.clip(np.ceil(freqs / half / df).astype(int), 1, FFT_N // 2)
        self._hi = np.clip(np.floor(freqs * half / df).astype(int) + 1, 1, FFT_N // 2 + 1)
        self._narrow = self._hi - self._lo < 3  # low end: band narrower than 3 FFT bins
        self._pos = freqs / df
        self._disp = np.full(len(freqs), FLOOR_DB)

    # --- lifecycle --------------------------------------------------------
    def start(self):
        if not HAVE_NUMPY or self._running:
            return
        self._running = True
        self._spawn()
        self._timer.start()

    def set_device(self, name):
        if name != self.device:
            self.device = name
            if self._running:
                self.stop()
                self.start()

    def stop(self):
        if not HAVE_NUMPY:
            return
        self._running = False
        self._timer.stop()
        self._link_timer.stop()
        if self._proc is not None:
            p, self._proc = self._proc, None
            p.finished.disconnect()
            p.terminate()
            if not p.waitForFinished(500):
                p.kill()
                p.waitForFinished(500)
            p.deleteLater()
        self._disp[:] = FLOOR_DB
        self.frame.emit(None)

    def _spawn(self):
        if not self._running or self._proc is not None:
            return
        if not self.device:
            return
        props = "{ node.passive=true node.name=tofu_eq.spectrum media.name=\"Tofu EQ spectrum\" }"
        args = ["--raw", "--format", "f32", "--channels", "2", "--rate", str(RATE), "--latency", "20ms",
                "--target", "0", "-P", props]
        p = QProcess(self)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(self._died)
        self._rest = b""
        p.start("pw-record", args + ["-"])
        self._proc = p
        self._link_tries = 0
        self._link_timer.start()

    def _link(self):
        """Link to the device monitor, retrying until our capture node has appeared."""
        self._link_tries += 1
        ok = True
        for ch in ("FL", "FR"):
            r = subprocess.run(["pw-link", f"{self.device}:monitor_{ch}", f"tofu_eq.spectrum:input_{ch}"],
                               capture_output=True)
            ok &= r.returncode == 0 or b"exists" in r.stderr
        if ok or self._link_tries >= 20:
            self._link_timer.stop()

    def _died(self, *_):
        if self._proc is not None:
            self._proc.deleteLater()
            self._proc = None
        if self._running:
            QTimer.singleShot(2000, self._spawn)  # e.g. PipeWire was restarted

    # --- data ---------------------------------------------------------------
    def _read(self):
        if self._proc is None:
            return
        data = self._rest + bytes(self._proc.readAllStandardOutput())
        n = len(data) // 8 * 8  # one f32 stereo frame = 8 bytes
        self._rest = data[n:]
        if n:
            new = np.frombuffer(data[:n], dtype=np.float32).reshape(-1, 2).mean(axis=1)[-FFT_N:]
            self._buf = np.roll(self._buf, -len(new))
            self._buf[-len(new):] = new
            self._fresh = True

    def _tick(self):
        if self._fresh:
            self._fresh = False
            spec = np.fft.rfft(self._buf * self._win)
            power = (spec.real ** 2 + spec.imag ** 2) * self._norm
            cs = np.concatenate(([0.0], np.cumsum(power)))
            band = cs[self._hi] - cs[self._lo]
            # low end: interpolate the 3-bin sum (whole Hann main lobe) so sine levels read correctly
            lobe = np.convolve(power, (1.0, 1.0, 1.0), mode="same")
            band = np.where(self._narrow, np.interp(self._pos, np.arange(len(lobe)), lobe), band)
            db = 10.0 * np.log10(np.maximum(band * 2.0, 1e-12))  # 0 dBFS = full-scale sine
            self._disp = np.maximum(db, self._disp - FALL_DB)
        elif self._disp.max() > FLOOR_DB:
            self._disp = np.maximum(self._disp - FALL_DB, FLOOR_DB)
        else:
            return  # stay idle (no repaint) while silent
        self.frame.emit(self._disp)
