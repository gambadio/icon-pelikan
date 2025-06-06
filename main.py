"""
main.py
Icon Pelikan — brutalist, grainy & ultra‑minimal GUI for lightning‑fast icon generation.
"""

import random
import sys
from pathlib import Path
import shutil # Added for rmtree

from PIL import Image

from PySide6.QtCore import (
    Qt,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QLinearGradient,
    QColor,
    QGuiApplication,
    QFont,
    QPainterPath,
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
    QToolTip,
    QGraphicsOpacityEffect,
)

from icon_processor import create_icon, export_iconset, to_icns


# ----------  Constants & assets ----------
ASSETS = Path(__file__).resolve().parent / "assets"
APP_ICON = ASSETS / "icon_pelikan.png"
NOISE_IMG = ASSETS / "noise.png"

BTN_MIN_W = 170  # keeps every button aligned
BTN_STYLE = """
QPushButton {
    color: #d8d9da;
    background-color: #3a3e47;
    border: 1px solid #4f545c;
    padding: 6px 14px;
    border-radius: 4px;
}
QPushButton:hover   { background-color: #4f545c; }
QPushButton:pressed { background-color: #282c34; }
QPushButton:disabled{
    background-color: #2a2d34;
    color: #6c6f73;
}
"""


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """Convert a Pillow RGBA image to QPixmap."""
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


# ----------  Background widget with gradient + noise  ----------
class ChromaticNoiseWidget(QWidget):
    """Paints a subtle radial gradient plus static grain texture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self.noise = self._ensure_noise()

    def paintEvent(self, ev):  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        rect = self.rect()

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#0e0e10"))
        grad.setColorAt(1.0, QColor("#2f3540"))
        painter.fillRect(rect, grad)            # gradient background

        painter.setOpacity(0.08)                # gentle grain overlay
        painter.drawPixmap(rect, self.noise)

    # ---------- helpers ----------
    def _ensure_noise(self) -> QPixmap:
        """Build a noise texture once & cache as PNG for subsequent runs."""
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


# ----------  Static rainbow header ----------
class StaticGradientLabel(QLabel):
    """Displays "ICON PELIKAN" with a static rainbow gradient."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignCenter)

        # Bold, large title font
        font = QFont("Helvetica Neue", 48, QFont.Bold)
        self.setFont(font)

    # ----------  Paint gradient text ----------
    def paintEvent(self, ev):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = self.rect()
        grad = QLinearGradient(rect.left(), 0, rect.right(), 0)

        # Orange → Red → Magenta → Purple → Blue
        stops = [
            (0.00, QColor("#ff6a00")),
            (0.33, QColor("#ff0066")),
            (0.66, QColor("#9b2eff")),
            (1.00, QColor("#0066ff")),
        ]
        for pos, col in stops:
            grad.setColorAt(pos, col)

        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)

        path = QPainterPath()
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        baseline = (rect.height() + fm.ascent() - fm.descent()) / 2
        x = (rect.width() - text_width) / 2
        path.addText(x, baseline, self.font(), self.text())

        painter.drawPath(path)


# ----------  Main window  ----------
class IconPelikan(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Pelikan")
        self.setWindowIcon(QPixmap(str(APP_ICON)))

        # runtime state
        self.source_img: Image.Image | None = None
        self.preview_img: Image.Image | None = None

        # value‑labels for sliders
        self.icon_sz_value_lbl: QLabel | None = None
        self.scale_sl_value_lbl: QLabel | None = None
        self.rad_sl_value_lbl: QLabel | None = None

        # central noise‑backdrop wrapper
        wrapper = ChromaticNoiseWidget()
        self.setCentralWidget(wrapper)

        # ----------  Preview pane ----------
        self.preview_label = QLabel(alignment=Qt.AlignCenter)
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self._set_initial_preview_text()

        # opacity‑fade effect whenever pixmap updates
        self._fade_eff = QGraphicsOpacityEffect(self.preview_label)
        self.preview_label.setGraphicsEffect(self._fade_eff)
        self._fade_anim = QPropertyAnimation(self._fade_eff, b"opacity", self)
        self._fade_anim.setDuration(250)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # ----------  Controls  ----------
        # 1.  Actions
        self.pick_colour_btn = QPushButton("Pick Colour")
        self.pick_colour_btn.clicked.connect(self.pick_colour)

        self.save_png_btn = QPushButton("Save PNG")
        self.save_png_btn.clicked.connect(self.save_png)

        self.save_icns_btn = QPushButton("Save .icns")
        self.save_icns_btn.clicked.connect(self.save_icns)

        # 2.  Sliders
        self.icon_sz = QSlider(Qt.Horizontal, minimum=128, maximum=1024, value=512)
        self.scale_sl = QSlider(Qt.Horizontal, minimum=50, maximum=100, value=86)
        self.rad_sl = QSlider(Qt.Horizontal, minimum=0, maximum=256, value=100)

        self.icon_sz.valueChanged.connect(self._update_icon_sz_display)
        self.scale_sl.valueChanged.connect(self._update_scale_display)
        self.rad_sl.valueChanged.connect(self._update_rad_display)

        # 3.  Shape combo
        self.shape_box = QComboBox()
        self.shape_box.addItems(["rounded", "circle"])
        self.shape_box.currentTextChanged.connect(self.rebuild)
        self.shape_box.setStyleSheet(self._combobox_style())

        # 4.  Presets
        self.presets = {
            "Default": {
                "canvas": 512,
                "scale": 86,
                "radius": 100,
                "shape": "rounded",
            },
            "macOS · 1024 px": {
                "canvas": 1024,
                "scale": 90,
                "radius": 180,
                "shape": "rounded",
            },
            "iOS · 1024 px": {
                "canvas": 1024,
                "scale": 100,
                "radius": 230,
                "shape": "rounded",
            },
            "Circle · 512 px": {
                "canvas": 512,
                "scale": 90,
                "radius": 256,
                "shape": "circle",
            },
            "Square · 512 px": {
                "canvas": 512,
                "scale": 100,
                "radius": 0,
                "shape": "rounded",
            },
        }
        self.preset_box = QComboBox()
        self.preset_box.addItems(list(self.presets.keys()))
        self.preset_box.currentTextChanged.connect(self.apply_preset)
        self.preset_box.setStyleSheet(self._combobox_style())

        # 5.  Misc
        self.bg_chk = QCheckBox("Solid background")
        self.bg_chk.toggled.connect(self.rebuild)
        self.bg_colour: QColor | None = QColor("#111111")

        self.remove_image_label = QLabel()
        self._setup_action_label(
            self.remove_image_label,
            "Remove Image",
            self.clear_image,
            href_action="#remove",
            font_size_pt=12,
        )
        self.remove_image_label.setStyleSheet("color:#ff6666;")
        self.remove_image_label.setVisible(False)

        # controls column
        ctrl_col = QVBoxLayout()
        ctrl_col.setSpacing(12)

        # Add Info label (no status bar)
        self.info_label = QLabel()
        self._setup_action_label(
            self.info_label,
            "Info",
            self.show_info_dialog,
            href_action="#info",
            font_size_pt=14,
        )
        # Adjusted style for bottom-left placement, removing specific padding
        self.info_label.setStyleSheet("color:#d8d9da; font-size:14pt;")
        # The info_label is no longer added to ctrl_col here.

        # ----------  Layout assembly ----------
        canvas_widget, self.icon_sz_value_lbl = self._labelled(
            "Canvas px", self.icon_sz, value_display=True
        )
        ctrl_col.addWidget(canvas_widget)

        scale_widget, self.scale_sl_value_lbl = self._labelled(
            "Scale %", self.scale_sl, value_display=True
        )
        ctrl_col.addWidget(scale_widget)

        radius_widget, self.rad_sl_value_lbl = self._labelled(
            "Radius px", self.rad_sl, value_display=True
        )
        ctrl_col.addWidget(radius_widget)

        shape_widget, _ = self._labelled("Shape", self.shape_box)
        ctrl_col.addWidget(shape_widget)

        preset_widget, _ = self._labelled("Preset", self.preset_box)
        ctrl_col.addWidget(preset_widget)

        ctrl_col.addWidget(self.bg_chk)
        ctrl_col.addWidget(self.pick_colour_btn)
        ctrl_col.addWidget(self.save_png_btn)
        ctrl_col.addWidget(self.save_icns_btn)
        ctrl_col.addWidget(self.remove_image_label)
        ctrl_col.addStretch(1)

        # apply uniform button styling / sizing
        for btn in (
            self.pick_colour_btn,
            self.save_png_btn,
            self.save_icns_btn,
        ):
            btn.setMinimumWidth(BTN_MIN_W)
            btn.setStyleSheet(BTN_STYLE)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # put controls in a QWidget so it can have its own QVBoxLayout margins
        controls_widget = QWidget()
        controls_widget.setLayout(ctrl_col)

        # 'wrapper' is the ChromaticNoiseWidget instance, set as the central widget.
        # Old layout:
        # root = QHBoxLayout(wrapper)
        # root.setContentsMargins(32, 32, 32, 32)
        # root.setSpacing(32)
        # root.addWidget(self.preview_label, 5)
        # root.addWidget(controls_widget, 2)

        # New layout structure for the main wrapper (ChromaticNoiseWidget)
        main_vertical_layout = QVBoxLayout(wrapper) # 'wrapper' is the ChromaticNoiseWidget
        main_vertical_layout.setContentsMargins(32, 32, 32, 32) # Overall window padding
        main_vertical_layout.setSpacing(20) # Space between top content and info_label below it

        # Animated rainbow title
        self.header_label = StaticGradientLabel("ICON PELIKAN")
        self.header_label.setFixedHeight(80)
        main_vertical_layout.addWidget(self.header_label, 0, Qt.AlignHCenter)

        # Container for the preview and controls (top part of the UI)
        top_content_area = QWidget()
        top_content_layout = QHBoxLayout(top_content_area)
        # Margins are handled by main_vertical_layout, so no margins here for top_content_layout itself
        top_content_layout.setContentsMargins(0, 0, 0, 0)
        top_content_layout.setSpacing(32) # Spacing between preview_label and controls_widget

        # --- Preview + “remove image” stacked vertically ---
        preview_container = QWidget()
        preview_vbox = QVBoxLayout(preview_container)
        preview_vbox.setContentsMargins(0, 0, 0, 0)
        preview_vbox.setSpacing(6)
        # keep the whole stack vertically centred in the available space
        preview_vbox.addStretch(1)
        preview_vbox.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        preview_vbox.addWidget(self.remove_image_label, alignment=Qt.AlignCenter)
        preview_vbox.addStretch(1)
        top_content_layout.addWidget(preview_container, 5)
        top_content_layout.addWidget(controls_widget, 2)

        main_vertical_layout.addWidget(top_content_area, 1) # Add top area, it takes most space (stretch 1)
        main_vertical_layout.addWidget(self.info_label, 0, Qt.AlignBottom | Qt.AlignLeft) # Add info_label at bottom-left

        # drag‑and‑drop
        self.setAcceptDrops(True)

        # initial slider labels
        self._update_icon_sz_display(self.icon_sz.value())
        self._update_scale_display(self.scale_sl.value())
        self._update_rad_display(self.rad_sl.value())

    # ----------  Slots / helpers ----------
    # 1.  Preset‑apply
    def apply_preset(self, name: str):
        if name not in self.presets:
            return
        cfg = self.presets[name]

        # block signals while we set values
        blockers = [
            self.icon_sz.blockSignals(True),
            self.scale_sl.blockSignals(True),
            self.rad_sl.blockSignals(True),
            self.shape_box.blockSignals(True),
        ]
        self.icon_sz.setValue(cfg["canvas"])
        self.scale_sl.setValue(cfg["scale"])
        self.rad_sl.setValue(cfg["radius"])
        self.shape_box.setCurrentText(cfg["shape"])

        # unblock
        self.icon_sz.blockSignals(False)
        self.scale_sl.blockSignals(False)
        self.rad_sl.blockSignals(False)
        self.shape_box.blockSignals(False)

        # refresh value‑labels + preview
        self._update_icon_sz_display(cfg["canvas"])
        self._update_scale_display(cfg["scale"])
        self._update_rad_display(cfg["radius"])
        self.rebuild()

    # 2.  Initial preview message
    def _set_initial_preview_text(self):
        font_pt = QApplication.font().pointSize() + 2
        self.preview_label.setTextFormat(Qt.RichText)
        self.preview_label.setText(
            f"<span style='color:#d8d9da; font-size:{font_pt}pt;'>"
            "Drop an image or click "
            "<a href='#open' style='color:#d8d9da; text-decoration:underline;'>Open</a>"
            "</span>"
        )
        # Ensure any previous connections are removed before reconnecting
        # to prevent multiple calls to _handle_preview_link.
        try:
            self.preview_label.linkActivated.disconnect()
        except RuntimeError:
            # This can happen if no connections exist yet, which is fine.
            pass
        self.preview_label.linkActivated.connect(self._handle_preview_link)

    # 3.  Handle preview link clicks
    def _handle_preview_link(self, href: str):
        """Handle clicks on links in the preview area."""
        if href == "#open":
            self.open_image()

    # 4.  Uniform label‑link helper
    @staticmethod
    def _setup_action_label(
        label: QLabel,
        text: str,
        slot_func,
        href_action: str,
        font_size_pt: int,
    ):
        label.setTextFormat(Qt.RichText)
        label.setText(
            f"<a href='{href_action}' style='color:#d8d9da; text-decoration:none; "
            f"font-size:{font_size_pt}pt;'>{text}</a>"
        )
        label.linkActivated.connect(lambda _: slot_func())

    # 4.  Slider wrappers
    def _labelled(
        self,
        header: str,
        widget: QWidget,
        value_display: bool = False,
    ) -> tuple[QWidget, QLabel | None]:
        hdr_lbl = QLabel(header)
        hdr_lbl.setStyleSheet("color:#d8d9da;")
        value_lbl = None

        header_row = QHBoxLayout()
        header_row.addWidget(hdr_lbl)

        if value_display:
            value_lbl = QLabel()
            value_lbl.setStyleSheet("color:#d8d9da; padding-left:6px;")
            value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            header_row.addWidget(value_lbl)
            header_row.setStretchFactor(hdr_lbl, 1)
            header_row.setStretchFactor(value_lbl, 0)

        box = QVBoxLayout()
        box.addLayout(header_row)
        box.addWidget(widget)
        container = QWidget()
        container.setLayout(box)
        return container, value_lbl

    def _update_icon_sz_display(self, v: int):
        if self.icon_sz_value_lbl:
            self.icon_sz_value_lbl.setText(f"{v}px")
        self.rebuild()

    def _update_scale_display(self, v: int):
        if self.scale_sl_value_lbl:
            self.scale_sl_value_lbl.setText(f"{v}%")
        self.rebuild()

    def _update_rad_display(self, v: int):
        if self.rad_sl_value_lbl:
            self.rad_sl_value_lbl.setText(f"{v}px")
        self.rebuild()

    # 5.  Colour‑picker
    def pick_colour(self):
        col = QColorDialog.getColor(
            self.bg_colour, self, options=QColorDialog.DontUseNativeDialog
        )
        if col.isValid():
            self.bg_colour = col
            self.bg_chk.setChecked(True)
            self.rebuild()

    # 6.  Drag‑and‑drop events
    def dragEnterEvent(self, ev):  # noqa: N802
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):  # noqa: N802
        for url in ev.mimeData().urls():
            if url.isLocalFile():
                self.load_image(Path(url.toLocalFile()))
                break

    # 7.  File actions
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
            self,
            "Save PNG",
            str(Path.home() / "icon.png"),
            "PNG (*.png)",
        )
        if path:
            self.preview_img.save(path)
            self._flash(f"Saved → {path}")

    def save_icns(self):
        if not self.preview_img:
            return

        default_save_path = Path.home() / "icon.icns"
        icns_save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save .icns File",
            str(default_save_path),
            "Apple Icon Image (*.icns)"
        )

        if not icns_save_path_str:
            return

        icns_save_path = Path(icns_save_path_str)
        # Use the chosen filename (without .icns) + .iconset as the temporary folder name
        temp_iconset_folder_path = icns_save_path.with_suffix(".iconset")

        try:
            # Make sure the temp folder doesn't exist
            if temp_iconset_folder_path.exists():
                shutil.rmtree(temp_iconset_folder_path)
                
            # Create the .iconset folder from the image
            export_iconset(self.preview_img, temp_iconset_folder_path)

            # Convert the .iconset folder to an .icns file
            created_icns_path = to_icns(temp_iconset_folder_path)
            
            # Ensure the file is at the location chosen by the user
            if created_icns_path.exists() and created_icns_path != icns_save_path and icns_save_path.parent.exists():
                # If the paths differ, we need to move the file
                created_icns_path.rename(icns_save_path)
            
            self._flash(f".icns generated at {icns_save_path}")

        except Exception as exc:
            QMessageBox.warning(
                self,
                "iconutil failed",
                "macOS `iconutil` couldn’t run or another error occurred.\n"
                "Ensure you’re on macOS and Xcode CLT are installed.\n\n"
                f"{exc}",
            )
        finally:
            # Clean up the temporary .iconset folder
            if temp_iconset_folder_path.exists() and temp_iconset_folder_path.is_dir():
                try:
                    shutil.rmtree(temp_iconset_folder_path)
                except Exception as e:
                    # Log or handle folder removal error if necessary
                    print(f"Error removing temporary folder {temp_iconset_folder_path}: {e}")

    # 8.  Core rebuild
    def load_image(self, path: Path):
        try:
            self.source_img = Image.open(path).convert("RGBA")
            self.remove_image_label.setVisible(True)
            self.rebuild()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Couldn’t open file:\n{exc}")

    def clear_image(self):
        # wipe state
        self.source_img = None
        self.preview_img = None
        self.remove_image_label.setVisible(False)

        # clear previous pixmap/text, then show the drag‑hint
        self.preview_label.clear()
        self._set_initial_preview_text()

        # refresh everything
        self.rebuild()

    def rebuild(self):
        if not self.source_img:
            return

        bg = (
            (self.bg_colour.red(), self.bg_colour.green(), self.bg_colour.blue(), 255)
            if self.bg_chk.isChecked() and self.bg_colour
            else None
        )

        self.preview_img = create_icon(
            self.source_img,
            icon_px=self.icon_sz.value(),
            scale=self.scale_sl.value() / 100,
            radius=self.rad_sl.value(),
            shape=self.shape_box.currentText(),
            background=bg,
        )
        pm = pil_to_qpixmap(self.preview_img)
        pm = pm.scaledToHeight(
            420, Qt.SmoothTransformation
        )  # fixed preview height for consistency
        self.preview_label.setPixmap(pm)
        self.preview_label.setText("")

        # fade‑in animation
        self._fade_anim.stop()
        self._fade_eff.setOpacity(0.0)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    # ----------  Misc ----------
    def show_info_dialog(self):
        """Show an informational dialog about the application."""
        box = QMessageBox(self)
        box.setWindowTitle("About Icon Pelikan")

        # Use the app icon instead of the default folder graphic
        icon_pm = QPixmap(str(APP_ICON)).scaled(
            96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        box.setIconPixmap(icon_pm)

        # Rich‑text content
        box.setTextFormat(Qt.RichText)
        box.setText(
            "<b>Icon Pelikan&nbsp;v0.1.0</b><br><br>"
            "A brutalist, grainy &amp; ultra‑minimal GUI for lightning‑fast icon generation."
            "<br><br>"
            "© 2025&nbsp;Ricardo Kupper<br>"
            "Built with PySide6 &amp; Python."
        )

        box.exec()

    def _combobox_style(self) -> str:
        return """
            QComboBox {
                color: #d8d9da;
                background-color: #2a2d34;
                border: 1px solid #4f545c;
                padding: 4px 22px 4px 6px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #4f545c;
                background-color: #2a2d34;
            }
            QComboBox QAbstractItemView {
                color: #d8d9da;
                background-color: #2a2d34;
                border: 1px solid #4f545c;
                selection-background-color: #58a6ff;
                selection-color: #ffffff;
            }
        """

    def _flash(self, text: str, msecs: int = 4000):
        """Bubble‑style toast using QToolTip centred on the window."""
        center = self.rect().center()
        global_center = self.mapToGlobal(center)
        QToolTip.showText(
            global_center, text, self, self.rect(), msecs
        )


# ----------  Bootstrap ----------
def main():
    QApplication.setApplicationName("Icon Pelikan")
    QApplication.setOrganizationName("Pelikan Co")
    app = QApplication(sys.argv)
    app.setFont(QFont("Helvetica Neue", 14))  # slightly larger default font

    w = IconPelikan()
    w.resize(QSize(960, 640))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()