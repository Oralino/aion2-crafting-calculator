"""Runs the market reader on a background thread so the window stays responsive."""

from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal, Slot

from aion2calc.data.recipes import Catalog
from aion2calc.ocr.market import MarketReader, MarketReading, NameMatcher


class _Worker(QObject):
    done = Signal(object)  # MarketReading
    failed = Signal(str)

    def __init__(self, catalog: Catalog) -> None:
        super().__init__()
        self._catalog = catalog
        self._reader: MarketReader | None = None

    @Slot(object)
    def read(self, image: Image.Image) -> None:
        try:
            if self._reader is None:  # loading the OCR models takes a moment; do it once
                names = {i: item.name for i, item in self._catalog.items.items()}
                self._reader = MarketReader(NameMatcher(names))
            self.done.emit(self._reader.read(image))
        except Exception as error:  # noqa: BLE001 - any failure is reported, never a crash
            self.failed.emit(f"{type(error).__name__}: {error}")


class CaptureReader(QObject):
    """Queue a screenshot with `read(image)`; get `done(MarketReading)` or `failed(str)`."""

    done = Signal(object)
    failed = Signal(str)
    _request = Signal(object)

    def __init__(self, catalog: Catalog, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.busy = False
        self._thread = QThread(self)
        self._worker = _Worker(catalog)
        self._worker.moveToThread(self._thread)
        self._request.connect(self._worker.read)
        self._worker.done.connect(self._finished)
        self._worker.failed.connect(self._failed)
        self._thread.start()

    def read(self, image: Image.Image) -> bool:
        """False if a capture is still being read."""
        if self.busy:
            return False
        self.busy = True
        self._request.emit(image)
        return True

    def _finished(self, reading: MarketReading) -> None:
        self.busy = False
        self.done.emit(reading)

    def _failed(self, message: str) -> None:
        self.busy = False
        self.failed.emit(message)

    def stop(self) -> None:
        """Let a read in progress finish (the first one loads the OCR models, which can take a
        while); destroying a running QThread aborts the app."""
        self._thread.quit()
        self._thread.wait()
