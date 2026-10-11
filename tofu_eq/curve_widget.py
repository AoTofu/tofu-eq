"""Frequency-response graph. Drag a handle for frequency/gain, scroll for Q."""
import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QMenu, QWidget

from . import dsp
from .i18n import tr

try:
    import numpy as np
except ImportError:  # only disables the spectrum overlay
    np = None

F_LO, F_HI = 20.0, 20000.0
DB_RANGE = 24.0
SPEC_RANGE = 80.0  # the spectrum maps -80..0 dBFS onto the full plot height
HANDLE_R = 9
BAND_COLORS = ["#e8615a", "#f0a030", "#d4c43a", "#5cc46a", "#3cb8c8", "#4a8ef0", "#9a6af0", "#e060b8"]


def band_color(i):
    return QColor(BAND_COLORS[i % len(BAND_COLORS)])


class CurveWidget(QWidget):
    bandEdited = Signal(int, dict)  # index, {freq/gain/q}
    bandSelected = Signal(int)
    addRequested = Signal(float, float)
    removeRequested = Signal(int)
    typeRequested = Signal(int, str)
    toggleRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.state = None
        self.rate = 48000
        self.selected = -1
        self._hover = -1
        self._drag = -1
        self._freqs = dsp.log_freqs()
        self._cache = {}
        self._spectrum = None
        self._xs = None
        self._bg_pm = None
        self._fg_pm = None

    # --- data ---------------------------------------------------------
    def set_state(self, state, rate):
        if rate != self.rate:
            self._xs = None
        self.state, self.rate = state, rate
        self._invalidate()

    def set_spectrum(self, db):
        self._spectrum = db
        self.update(self._plot().toAlignedRect())

    def set_selected(self, i):
        self.selected = i
        self._invalidate()

    def _band_curve(self, b):
        key = (b.type, b.freq, b.gain, b.q, self.rate)
        cur = self._cache.get(key)
        if cur is None:
            if len(self._cache) > 256:
                self._cache.clear()
            cf = dsp.coeffs(b.type, b.freq, b.gain, b.q, self.rate)
            cur = self._cache[key] = [dsp.magnitude_db(cf, f, self.rate) for f in self._freqs]
        return cur

    def eq_peak_db(self):
        """Peak of the combined response of all enabled bands (excluding the preamp)."""
        if not self.state:
            return 0.0
        total = [0.0] * len(self._freqs)
        for b in self.state.bands:
            if b.enabled:
                total = [t + v for t, v in zip(total, self._band_curve(b))]
        return max(total)

    # --- geometry -------------------------------------------------------
    def _plot(self):
        return QRectF(44, 10, self.width() - 56, self.height() - 34)

    def _x(self, f, r):
        return r.left() + r.width() * math.log(f / F_LO) / math.log(F_HI / F_LO)

    def _y(self, db, r):
        db = max(-DB_RANGE, min(DB_RANGE, db))
        return r.top() + r.height() * (DB_RANGE - db) / (2 * DB_RANGE)

    def _f_at(self, x, r):
        t = (x - r.left()) / r.width()
        return F_LO * (F_HI / F_LO) ** max(0.0, min(1.0, t))

    def _db_at(self, y, r):
        return DB_RANGE - (y - r.top()) / r.height() * 2 * DB_RANGE

    def _handle_pos(self, b, r):
        g = b.gain if b.type in dsp.GAIN_TYPES else 0.0
        return QPointF(self._x(min(max(b.freq, F_LO), F_HI), r), self._y(g, r))

    def _hit(self, pos):
        if not self.state:
            return -1
        r = self._plot()
        best, best_d = -1, (HANDLE_R + 4) ** 2
        for i, b in enumerate(self.state.bands):
            p = self._handle_pos(b, r)
            d = (p.x() - pos.x()) ** 2 + (p.y() - pos.y()) ** 2
            if d <= best_d:
                best, best_d = i, d
        return best

    # --- painting -------------------------------------------------------
    # The grid and EQ curves are cached in a QPixmap; only the spectrum is redrawn every frame.
    def _invalidate(self, background=False):
        self._fg_pm = None
        if background:
            self._bg_pm = None
        self.update()

    def resizeEvent(self, ev):
        self._xs = None
        self._invalidate(background=True)
        super().resizeEvent(ev)

    def changeEvent(self, ev):
        if ev.type() in (QEvent.PaletteChange, QEvent.StyleChange, QEvent.FontChange):
            self._invalidate(background=True)
        super().changeEvent(ev)

    def _layer(self, paint):
        dpr = self.devicePixelRatioF()
        pm = QPixmap(round(self.width() * dpr), round(self.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        paint(p, self._plot())
        p.end()
        return pm

    def paintEvent(self, ev):
        if self._bg_pm is None:
            self._bg_pm = self._layer(self._paint_background)
        if self._fg_pm is None:
            # Merge the background and EQ curves into one opaque image (each frame = plain blit + spectrum).
            self._fg_pm = self._bg_pm.copy()
            p = QPainter(self._fg_pm)
            p.setRenderHint(QPainter.Antialiasing)
            self._paint_foreground(p, self._plot())
            p.end()
        p = QPainter(self)
        p.setClipRect(ev.rect())
        p.drawPixmap(0, 0, self._fg_pm)
        if self._spectrum is not None:
            self._paint_spectrum(p, self._plot())

    def _paint_background(self, p, r):
        pal = self.palette()
        fg = pal.text().color()
        p.fillRect(self.rect(), pal.window().color())
        p.fillRect(r, pal.base().color())
        grid = QColor(fg)
        grid.setAlpha(28)
        label = QColor(fg)
        label.setAlpha(150)
        font = p.font()
        font.setPointSizeF(font.pointSizeF() * 0.85)
        p.setFont(font)
        for f in (20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900,
                  1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000):
            x = self._x(f, r)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            if f in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000):
                p.setPen(label)
                txt = f"{f // 1000}k" if f >= 1000 else str(f)
                p.drawText(QRectF(x - 20, r.bottom() + 2, 40, 18), Qt.AlignHCenter | Qt.AlignTop, txt)
        for db in range(-24, 25, 6):
            y = self._y(db, r)
            g = QColor(grid)
            if db == 0:
                g.setAlpha(80)
            p.setPen(QPen(g, 1))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(label)
            p.drawText(QRectF(0, y - 9, r.left() - 6, 18), Qt.AlignRight | Qt.AlignVCenter, f"{db:+d}" if db else "0")

    def _paint_foreground(self, p, r):
        if not self.state:
            return
        pal = self.palette()
        bg = pal.base().color()
        fg = pal.text().color()
        p.setClipRect(r)
        xs = self._plot_xs(r)
        bypass = self.state.bypass
        total = [0.0] * len(self._freqs)
        y0 = self._y(0, r)
        for i, b in enumerate(self.state.bands):
            cur = self._band_curve(b)
            if not b.enabled:
                continue
            total = [t + v for t, v in zip(total, cur)]
            col = band_color(i)
            col.setAlpha(60 if i == self.selected else 28)
            poly = QPolygonF([QPointF(xs[0], y0)] + [QPointF(x, self._y(v, r)) for x, v in zip(xs, cur)] + [QPointF(xs[-1], y0)])
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawPolygon(poly)

        path = QPainterPath()
        pre = self.state.preamp
        for k, (x, v) in enumerate(zip(xs, total)):
            pt = QPointF(x, self._y(0.0 if bypass else v + pre, r))
            path.moveTo(pt) if k == 0 else path.lineTo(pt)
        line = QColor(fg) if not bypass else QColor(fg.red(), fg.green(), fg.blue(), 90)
        if not bypass and max(total) + pre > 0.05:
            line = QColor("#e8615a")  # may clip
        p.setPen(QPen(line, 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.setClipping(False)

        font = p.font()
        font.setPointSizeF(font.pointSizeF() * 0.85)
        p.setFont(font)
        for i, b in enumerate(self.state.bands):
            c = self._handle_pos(b, r)
            col = band_color(i)
            if not b.enabled:
                col.setAlpha(80)
            rad = HANDLE_R + (2 if i in (self.selected, self._hover) else 0)
            p.setPen(QPen(fg if i == self.selected else bg, 2))
            p.setBrush(col)
            p.drawEllipse(c, rad, rad)
            p.setPen(bg if b.enabled else fg)
            p.drawText(QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad), Qt.AlignCenter, str(i + 1))

    def _plot_xs(self, r):
        if self._xs is None:
            self._xs = [self._x(f, r) for f in self._freqs]
        return self._xs

    def _paint_spectrum(self, p, r):
        xs = self._plot_xs(r)
        ys = r.top() - np.clip(self._spectrum, -SPEC_RANGE, 0.0) * (r.height() / SPEC_RANGE)
        pts = [QPointF(x, y) for x, y in zip(xs, ys.tolist())]
        fg = self.palette().text().color()
        fill = QColor(fg)
        fill.setAlpha(22)
        edge = QColor(fg)
        edge.setAlpha(45)
        p.setClipRect(r)
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawPolygon(QPolygonF([QPointF(xs[0], r.bottom())] + pts + [QPointF(xs[-1], r.bottom())]))
        p.setPen(QPen(edge, 1))
        p.drawPolyline(QPolygonF(pts))

    # --- interaction ----------------------------------------------------
    def mousePressEvent(self, ev):
        i = self._hit(ev.position())
        if ev.button() == Qt.LeftButton and i >= 0:
            self._drag = i
            self.bandSelected.emit(i)
        elif ev.button() == Qt.RightButton and i >= 0:
            self.bandSelected.emit(i)
            self._context_menu(i, ev.globalPosition().toPoint())

    def mouseMoveEvent(self, ev):
        r = self._plot()
        if self._drag >= 0 and self.state:
            b = self.state.bands[self._drag]
            pos = ev.position()
            edit = {"freq": round(self._f_at(pos.x(), r), 1)}
            if b.type in dsp.GAIN_TYPES:
                edit["gain"] = round(max(-DB_RANGE, min(DB_RANGE, self._db_at(pos.y(), r))), 1)
            self.bandEdited.emit(self._drag, edit)
        else:
            h = self._hit(ev.position())
            if h != self._hover:
                self._hover = h
                self.setCursor(Qt.SizeAllCursor if h >= 0 else Qt.ArrowCursor)
                self._invalidate()

    def mouseReleaseEvent(self, _ev):
        self._drag = -1

    def mouseDoubleClickEvent(self, ev):
        r = self._plot()
        if ev.button() == Qt.LeftButton and self._hit(ev.position()) < 0 and r.contains(ev.position()):
            self.addRequested.emit(round(self._f_at(ev.position().x(), r), 1), round(self._db_at(ev.position().y(), r), 1))

    def wheelEvent(self, ev):
        i = self._hit(ev.position())
        if i < 0:
            i = self.selected
        if i < 0 or not self.state:
            return
        steps = ev.angleDelta().y() / 120.0
        b = self.state.bands[i]
        self.bandSelected.emit(i)
        self.bandEdited.emit(i, {"q": round(max(0.05, min(30.0, b.q * 1.12 ** steps)), 3)})
        ev.accept()

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.selected >= 0:
            self.removeRequested.emit(self.selected)
        else:
            super().keyPressEvent(ev)

    def _context_menu(self, i, gpos):
        b = self.state.bands[i]
        m = QMenu(self)
        for t in dsp.TYPES:
            a = m.addAction(tr(dsp.LABELS[t]))
            a.setCheckable(True)
            a.setChecked(t == b.type)
            a.triggered.connect(lambda _=False, t=t: self.typeRequested.emit(i, t))
        m.addSeparator()
        m.addAction(tr("Disable") if b.enabled else tr("Enable")).triggered.connect(lambda: self.toggleRequested.emit(i))
        m.addAction(tr("Delete")).triggered.connect(lambda: self.removeRequested.emit(i))
        m.exec(gpos)
