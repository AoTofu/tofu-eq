import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from . import __version__, i18n
from .main_window import MainWindow


def main():
    if "--version" in sys.argv:
        print(f"tofu-eq {__version__}")
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName("tofu-eq")
    app.setApplicationDisplayName("Tofu EQ")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("tofu-eq")
    saved = QSettings("tofu-eq", "tofu-eq").value("language", "auto")
    i18n.set_language(i18n.resolve(None if saved == "auto" else saved))

    windows = []

    def open_window(geometry=None):
        w = MainWindow(relaunch=open_window)
        if geometry is not None:
            w.restoreGeometry(geometry)
        w.show()
        windows[:] = [w]

    open_window()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
