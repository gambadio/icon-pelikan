"""
main.py
Icon Pelikan — brutalist grainy dark GUI for fast icon generation.
"""

import os
import random
import sys
from pathlib import Path

from PIL import Image

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QLinearGradient,
    QColor,
    QAction,
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFileDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QComboBox,
    QColorDialog,
    QCheckBox,
    QMessageBox,
    QSizePolicy,
)

from icon_processor import create_icon, export_iconset, to_icns


ASSETS = Path(__file__).resolve().parent / "assets"
APP_ICON = ASSETS / "icon_pelikan.png"
NOISE_IMG = ASSETS / "noise.png"


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """Convert a Pillow RGBA image to QPixmap."""
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


# ----------  Background widget with gradient + noise  ----------
class ChromaticNoiseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self.noise = self._ensure_noise()

    # paintEvent → radial gradient + overlaid noise texture
    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, QColor("#0e0e10"))
        grad.setColorAt(1.0, QColor("#2f3540"))
        painter.fillRect(rect, grad)                  # gradient background

        painter.setOpacity(0.08)                      # gentle grain
        painter.drawPixmap(rect, self.noise)

    def _ensure_noise(self) -> QPixmap:
        """Build a noise texture once + cache as PNG for subsequent runs."""
        if not NOISE_IMG.exists():
            NOISE_IMG.parent.mkdir(parents=True, exist_ok=True)
            w = h = 512
            img = Image.new("L", (w, h))
            px = img.load()
            for y in range(h):
                for x in range(w):
                    px[x, y] = random.randint(0, 255)
            img.save(NOISE_IMG)
        return QPixmap(str(NOISE_IMG))


# ----------  Main window  ----------
class IconPelikan(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Pelikan")
        self.setWindowIcon(QPixmap(str(APP_ICON)))

        self.source_img: Image.Image | None = None
        self.preview_img: Image.Image | None = None

        wrapper = ChromaticNoiseWidget()
        self.setCentralWidget(wrapper)

        # ----- preview pane -----
        self.preview_label = QLabel("Drop an image or click ‘Open’")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color:#d8d9da; font-size:14px;")
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ----- controls -----
        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self.open_image)

        save_png_btn = QPushButton("Save PNG")
        save_png_btn.clicked.connect(self.save_png)

        save_icns_btn = QPushButton("Save .icns")
        save_icns_btn.clicked.connect(self.save_icns)

        # sliders
        self.icon_sz = QSlider(Qt.Horizontal, minimum=128, maximum=1024, value=512)
        self.scale_sl = QSlider(Qt.Horizontal, minimum=50, maximum=100, value=86)
        self.rad_sl = QSlider(Qt.Horizontal, minimum=0, maximum=256, value=100)
        for sl in (self.icon_sz, self.scale_sl, self.rad_sl):
            sl.valueChanged.connect(self.rebuild)

        shape_box = QComboBox()
        shape_box.addItems(["rounded", "circle"])
        shape_box.currentTextChanged.connect(self.rebuild)
        self.shape_box = shape_box

        self.bg_chk = QCheckBox("Solid background")
        self.bg_chk.toggled.connect(self.rebuild)
        self.bg_colour: QColor | None = QColor("#111111")
        colour_btn = QPushButton("Pick colour")
        colour_btn.clicked.connect(self.pick_colour)

        # layout
        ctrl_col = QVBoxLayout()
        ctrl_col.addWidget(open_btn)
        ctrl_col.addWidget(self._labelled("Canvas px", self.icon_sz))
        ctrl_col.addWidget(self._labelled("Scale %", self.scale_sl))
        ctrl_col.addWidget(self._labelled("Radius px", self.rad_sl))
        ctrl_col.addWidget(self._labelled("Shape", shape_box))
        ctrl_col.addWidget(self.bg_chk)
        ctrl_col.addWidget(colour_btn)
        ctrl_col.addWidget(save_png_btn)
        ctrl_col.addWidget(save_icns_btn)
        ctrl_col.addStretch(1)

        root = QHBoxLayout(wrapper)
        root.setContentsMargins(32, 32, 32, 32)
        root.addWidget(self.preview_label, 4)
        root.addLayout(ctrl_col, 2)

        # drag-and-drop
        self.setAcceptDrops(True)

        # menu bar tiny ‘About’
        about = QAction("About Icon Pelikan …", self)
        about.triggered.connect(
            lambda: QMessageBox.information(
                self,
                "About Icon Pelikan",
                "A tiny brutalist icon generator written in Python (PySide 6 + Pillow).",
            )
        )
        self.menuBar().addAction(about)

    # ---------- helpers ----------
    def _labelled(self, text: str, widget: QWidget) -> QWidget:
        label = QLabel(text)
        label.setStyleSheet("color:#d8d9da;")
        box = QVBoxLayout()
        box.addWidget(label)
        box.addWidget(widget)
        w = QWidget()
        w.setLayout(box)
        return w

    def pick_colour(self):
        col = QColorDialog.getColor(self.bg_colour, self, options=QColorDialog.DontUseNativeDialog)
        if col.isValid():
            self.bg_colour = col
            self.bg_chk.setChecked(True)
            self.rebuild()

    # ---------- drag-and-drop ----------
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        for url in ev.mimeData().urls():
            if url.isLocalFile():
                self.load_image(Path(url.toLocalFile()))
                break

    # ---------- file actions ----------
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.tiff *.bmp)",
        )
        if path:
            self.load_image(Path(path))

    def save_png(self):
        if not self.preview_img:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PNG", str(Path.home() / "icon.png"), "PNG (*.png)"
        )
        if path:
            self.preview_img.save(path)
            self.statusBar().showMessage(f"Saved → {path}", 4000)

    def save_icns(self):
        if not self.preview_img:
            return
        dest = QFileDialog.getExistingDirectory(self, "Pick folder")
        if dest:
            icn = self.preview_img
            out = export_iconset(icn, Path(dest))
            try:
                icns_path = to_icns(out)
                self.statusBar().showMessage(f".icns generated at {icns_path}", 6000)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "iconutil failed",
                    "macOS `iconutil` couldn’t run.\n"
                    "Ensure you’re on macOS and Xcode CLT are installed.\n\n"
                    f"{e}",
                )

    # ---------- core ----------
    def load_image(self, path: Path):
        try:
            self.source_img = Image.open(path).convert("RGBA")
            self.rebuild()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Couldn’t open file:\n{exc}")

    def rebuild(self):
        if not self.source_img:
            return

        bg = None
        if self.bg_chk.isChecked() and self.bg_colour:
            c = self.bg_colour
            bg = (c.red(), c.green(), c.blue(), 255)

        self.preview_img = create_icon(
            self.source_img,
            icon_px=self.icon_sz.value(),
            scale=self.scale_sl.value() / 100,
            radius=self.rad_sl.value(),
            shape=self.shape_box.currentText(),
            background=bg,
        )
        pm = pil_to_qpixmap(self.preview_img)
        self.preview_label.setPixmap(pm.scaledToHeight(400, Qt.SmoothTransformation))
        self.preview_label.setText("")

# ----------  Bootstrap  ----------
def main():
    QApplication.setApplicationName("Icon Pelikan")
    QApplication.setOrganizationName("Pelikan Co")
    app = QApplication(sys.argv)

    # enable high-DPI
    QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    w = IconPelikan()
    w.resize(QSize(900, 600))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()