# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
"""Settings page shown in QGIS Settings > Options and direct plugin Settings dialog."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory

from .core.earth import detect_earth_pro

PAGE_TITLE = "Lazy Earth & Maps"

TARGETS = [
    ("auto", "Auto (Earth Pro if found, else Earth Web)"),
    ("pro", "Google Earth Pro (desktop)"),
    ("web", "Google Earth Web (browser)"),
]
BASEMAPS = [
    ("roadmap", "Roadmap"),
    ("satellite", "Satellite"),
    ("terrain", "Terrain"),
]
FORMATS = [
    ("kmz", "KMZ (compressed, recommended)"),
    ("kml", "KML (plain text)"),
]
SV_ICONS = [
    ("streetview", "Official Google Street View Icon"),
    ("pegman", "Official Google Pegman"),
]


def _combo(items, current):
    cb = QComboBox()
    for key, label in items:
        cb.addItem(label, key)
    idx = cb.findData(current)
    cb.setCurrentIndex(max(0, idx))
    return cb


def _row(*widgets):
    holder, lay = QWidget(), QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    for w in widgets:
        lay.addWidget(w)
    holder.setLayout(lay)
    return holder


class LazySettingsWidget(QWidget):
    """Reusable settings form used by both QgsOptionsPageWidget and standalone QDialog."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._s = settings
        self._setup_ui()

    def _setup_ui(self):
        s = self._s
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget(self)

        # Tab 1: Toolbar & Buttons
        tab_toolbar = QWidget()
        lay_tb = QVBoxLayout(tab_toolbar)
        box_tb = QGroupBox("Toolbar & Menu Actions")
        f_tb = QFormLayout(box_tb)

        self.show_maps = QCheckBox("Show Google Maps button")
        self.show_maps.setChecked(s.get("show_maps"))

        self.show_sv = QCheckBox("Show Street View picker button")
        self.show_sv.setChecked(s.get("show_streetview"))

        self.show_cov = QCheckBox("Show Street View Coverage layer toggle button")
        self.show_cov.setChecked(s.get("show_coverage"))

        self.show_fly = QCheckBox("Show 'Open in Earth' button (view only, no export)")
        self.show_fly.setChecked(s.get("show_earth_fly"))

        self.show_send = QCheckBox("Show 'Export & send to Earth' button (KML/KMZ)")
        self.show_send.setChecked(s.get("show_earth_send"))

        for w in (self.show_maps, self.show_sv, self.show_cov, self.show_fly, self.show_send):
            f_tb.addRow(w)

        self.sv_icon = _combo(SV_ICONS, s.get("sv_icon_style"))
        f_tb.addRow("Street View icon style:", self.sv_icon)

        lay_tb.addWidget(box_tb)
        lay_tb.addStretch(1)
        tabs.addTab(tab_toolbar, "Toolbar")

        # Tab 2: Google Maps & Street View
        tab_maps = QWidget()
        lay_m = QVBoxLayout(tab_maps)

        box_m = QGroupBox("Google Maps Options")
        f_m = QFormLayout(box_m)
        self.basemap = _combo(BASEMAPS, s.get("maps_basemap"))
        f_m.addRow("Default map style:", self.basemap)
        lay_m.addWidget(box_m)

        box_sv = QGroupBox("Street View & Coverage Overlay")
        f_sv = QFormLayout(box_sv)
        self.auto_cov = QCheckBox("Auto-show Street View coverage (blue lines) when clicking Street View picker")
        self.auto_cov.setChecked(s.get("auto_show_coverage"))
        f_sv.addRow(self.auto_cov)

        info_lbl = QLabel(
            "<i>Note: Street View coverage uses Google's public XYZ tile service. "
            "No API keys or billing required.</i>"
        )
        info_lbl.setWordWrap(True)
        f_sv.addRow(info_lbl)
        lay_m.addWidget(box_sv)
        lay_m.addStretch(1)
        tabs.addTab(tab_maps, "Maps & Street View")

        # Tab 3: Google Earth
        tab_earth = QWidget()
        lay_e = QVBoxLayout(tab_earth)
        box_e = QGroupBox("Google Earth Options")
        f_e = QFormLayout(box_e)

        self.target = _combo(TARGETS, s.get("earth_target"))
        f_e.addRow("Open exported layers in:", self.target)

        self.path = QLineEdit(s.get("earth_pro_path"))
        self.path.setPlaceholderText("Empty = auto-detect / Earth Web")
        b_det, b_br = QPushButton("Auto-Detect"), QPushButton("Browse...")
        b_det.clicked.connect(self._detect_pro)
        b_br.clicked.connect(self._browse_exe)
        f_e.addRow("Google Earth Pro location:", _row(self.path, b_det, b_br))

        self.tilt = QSpinBox()
        self.tilt.setRange(0, 80)
        self.tilt.setSuffix(" deg")
        self.tilt.setValue(int(s.get("earth_tilt")))
        f_e.addRow("Camera tilt (0 = top-down):", self.tilt)

        lay_e.addWidget(box_e)
        lay_e.addStretch(1)
        tabs.addTab(tab_earth, "Google Earth")

        # Tab 4: KML / KMZ Export
        tab_exp = QWidget()
        lay_x = QVBoxLayout(tab_exp)
        box_x = QGroupBox("Layer Export Configuration")
        f_x = QFormLayout(box_x)

        self.fmt = _combo(FORMATS, s.get("export_format"))
        f_x.addRow("Default export format:", self.fmt)

        self.export_dir = QLineEdit(s.get("export_dir"))
        self.export_dir.setPlaceholderText("Empty = system temp folder")
        b_dir = QPushButton("Browse...")
        b_dir.clicked.connect(self._browse_dir)
        f_x.addRow("Export folder:", _row(self.export_dir, b_dir))

        self.cap = QSpinBox()
        self.cap.setRange(100, 500000)
        self.cap.setSingleStep(1000)
        self.cap.setValue(int(s.get("feature_cap")))
        f_x.addRow("Max features per export:", self.cap)

        self.attrs = QCheckBox("Include attribute table as pop-up data")
        self.attrs.setChecked(s.get("include_attrs"))
        f_x.addRow(self.attrs)

        self.folder = QCheckBox("Earth Web hand-off: also open the export folder")
        self.folder.setChecked(s.get("open_folder_on_web"))
        f_x.addRow(self.folder)

        self.labels = QLineEdit(s.get("label_fields"))
        f_x.addRow("Label field priority (comma-separated):", self.labels)

        lay_x.addWidget(box_x)
        lay_x.addStretch(1)
        tabs.addTab(tab_exp, "Export")

        root.addWidget(tabs)

    def _detect_pro(self):
        detected = detect_earth_pro()
        if detected:
            self.path.setText(detected)
        else:
            QMessageBox.information(
                self, "Google Earth Pro",
                "Google Earth Pro was not detected in standard system locations.\n"
                "You can specify its location manually using the Browse button."
            )

    def _browse_exe(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Google Earth Pro Executable", "", "")
        if p:
            self.path.setText(p)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Export Folder", self.export_dir.text())
        if d:
            self.export_dir.setText(d)

    def apply_settings(self):
        s = self._s
        s.set("show_maps", self.show_maps.isChecked())
        s.set("show_streetview", self.show_sv.isChecked())
        s.set("show_coverage", self.show_cov.isChecked())
        s.set("show_earth_fly", self.show_fly.isChecked())
        s.set("show_earth_send", self.show_send.isChecked())
        s.set("sv_icon_style", self.sv_icon.currentData())
        s.set("maps_basemap", self.basemap.currentData())
        s.set("auto_show_coverage", self.auto_cov.isChecked())
        s.set("earth_target", self.target.currentData())
        s.set("earth_pro_path", self.path.text().strip())
        s.set("earth_tilt", self.tilt.value())
        s.set("export_format", self.fmt.currentData())
        s.set("export_dir", self.export_dir.text().strip())
        s.set("feature_cap", self.cap.value())
        s.set("include_attrs", self.attrs.isChecked())
        s.set("open_folder_on_web", self.folder.isChecked())
        s.set("label_fields", self.labels.text().strip() or "name,title,label,id")

    def reset_defaults(self):
        self._s.reset_defaults()
        s = self._s
        self.show_maps.setChecked(s.get("show_maps"))
        self.show_sv.setChecked(s.get("show_streetview"))
        self.show_cov.setChecked(s.get("show_coverage"))
        self.show_fly.setChecked(s.get("show_earth_fly"))
        self.show_send.setChecked(s.get("show_earth_send"))
        i_sv = self.sv_icon.findData(s.get("sv_icon_style"))
        self.sv_icon.setCurrentIndex(max(0, i_sv))
        i_bm = self.basemap.findData(s.get("maps_basemap"))
        self.basemap.setCurrentIndex(max(0, i_bm))
        self.auto_cov.setChecked(s.get("auto_show_coverage"))
        i_tg = self.target.findData(s.get("earth_target"))
        self.target.setCurrentIndex(max(0, i_tg))
        self.path.setText(s.get("earth_pro_path"))
        self.tilt.setValue(int(s.get("earth_tilt")))
        i_fmt = self.fmt.findData(s.get("export_format"))
        self.fmt.setCurrentIndex(max(0, i_fmt))
        self.export_dir.setText(s.get("export_dir"))
        self.cap.setValue(int(s.get("feature_cap")))
        self.attrs.setChecked(s.get("include_attrs"))
        self.folder.setChecked(s.get("open_folder_on_web"))
        self.labels.setText(s.get("label_fields"))


class LazySettingsDialog(QDialog):
    """Direct Settings Dialog opened from Plugins > Lazy Earth & Maps > Settings..."""

    def __init__(self, settings, on_apply, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lazy Earth & Maps - Settings")
        self.setMinimumWidth(560)
        self._s = settings
        self._on_apply = on_apply

        lay = QVBoxLayout(self)
        self.form = LazySettingsWidget(settings, self)
        lay.addWidget(self.form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.form.reset_defaults)
        lay.addWidget(btn_box)

    def _accept(self):
        self.form.apply_settings()
        if self._on_apply:
            self._on_apply()
        self.accept()


class LazyOptionsPage(QgsOptionsPageWidget):
    """QGIS Settings > Options integration."""

    def __init__(self, settings, on_apply, parent=None):
        super().__init__(parent)
        self._s, self._on_apply = settings, on_apply
        lay = QVBoxLayout(self)
        self.form = LazySettingsWidget(settings, self)
        lay.addWidget(self.form)

    def apply(self):
        self.form.apply_settings()
        if self._on_apply:
            self._on_apply()


class LazyOptionsFactory(QgsOptionsWidgetFactory):
    def __init__(self, settings, icon, on_apply):
        super().__init__()
        self._settings, self._icon, self._on_apply = settings, icon, on_apply

    def title(self):
        return PAGE_TITLE

    def icon(self):
        return self._icon

    def createWidget(self, parent=None):
        return LazyOptionsPage(self._settings, self._on_apply, parent)
