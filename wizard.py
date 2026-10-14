# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
from qgis.PyQt.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QComboBox,
    QLineEdit, QPushButton, QSpinBox, QCheckBox, QFileDialog, QFormLayout, QWidget,
)

from .core.earth import detect_earth_pro

TARGETS = [("auto", "Auto (Earth Pro if found, else Earth Web)"),
           ("pro", "Google Earth Pro (desktop)"), ("web", "Google Earth Web (browser)")]
BASEMAPS = [("roadmap", "Roadmap"), ("satellite", "Satellite"), ("terrain", "Terrain")]
FORMATS = [("kmz", "KMZ (compressed, recommended)"), ("kml", "KML (plain text)")]


def _combo(items, current):
    cb = QComboBox()
    for key, label in items:
        cb.addItem(label, key)
    i = cb.findData(current)
    cb.setCurrentIndex(max(0, i))
    return cb


class _ProfilePage(QWizardPage):
    def __init__(self, s):
        super().__init__()
        self.setTitle("What do you want on your toolbar?")
        self.setSubTitle("Pick which buttons to show. You can re-run this wizard any time from the Web menu.")
        lay = QVBoxLayout(self)
        self.show_maps = QCheckBox("Google Maps button (views, Street View, pins)")
        self.show_maps.setChecked(s.get("show_maps"))
        self.show_sv = QCheckBox("Street View button (click map to open Street View there)")
        self.show_sv.setChecked(s.get("show_streetview"))
        self.show_fly = QCheckBox("Open in Google Earth button (view only, no export)")
        self.show_fly.setChecked(s.get("show_earth_fly"))
        self.show_send = QCheckBox("Export & send to Google Earth button (KML/KMZ)")
        self.show_send.setChecked(s.get("show_earth_send"))
        for w in (self.show_maps, self.show_sv, self.show_fly, self.show_send):
            lay.addWidget(w)
        form = QFormLayout()
        self.basemap = _combo(BASEMAPS, s.get("maps_basemap"))
        form.addRow("Default Google Maps style:", self.basemap)
        w = QWidget(); w.setLayout(form); lay.addWidget(w)


class _EarthPage(QWizardPage):
    def __init__(self, s):
        super().__init__()
        self.setTitle("Google Earth setup")
        self.setSubTitle("Earth Web cannot auto-load a file from a link, so Earth Pro is the smoothest "
                         "route for layers. Earth Web still works via a guided hand-off.")
        form = QFormLayout(self)
        self.target = _combo(TARGETS, s.get("earth_target"))
        form.addRow("Open layers in:", self.target)
        row = QHBoxLayout()
        self.path = QLineEdit(s.get("earth_pro_path") or detect_earth_pro())
        self.path.setPlaceholderText("Not found - leave empty to use Earth Web")
        b_det, b_br = QPushButton("Detect"), QPushButton("Browse...")
        b_det.clicked.connect(lambda: self.path.setText(detect_earth_pro()))
        b_br.clicked.connect(self._browse)
        for w in (self.path, b_det, b_br):
            row.addWidget(w)
        holder = QWidget(); holder.setLayout(row)
        form.addRow("Earth Pro location:", holder)
        self.tilt = QSpinBox(); self.tilt.setRange(0, 80); self.tilt.setSuffix(" deg")
        self.tilt.setValue(int(s.get("earth_tilt")))
        form.addRow("Fly-to camera tilt (0 = top-down):", self.tilt)
        self.fmt = _combo(FORMATS, s.get("export_format"))
        form.addRow("Export format:", self.fmt)
        self.cap = QSpinBox(); self.cap.setRange(100, 500000); self.cap.setSingleStep(1000)
        self.cap.setValue(int(s.get("feature_cap")))
        form.addRow("Max features per send:", self.cap)
        self.attrs = QCheckBox("Include attribute table as pop-up data"); self.attrs.setChecked(s.get("include_attrs"))
        form.addRow(self.attrs)
        self.folder = QCheckBox("Earth Web hand-off: also open the export folder"); self.folder.setChecked(s.get("open_folder_on_web"))
        form.addRow(self.folder)
        self.labels = QLineEdit(s.get("label_fields"))
        form.addRow("Label field priority (comma list):", self.labels)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Google Earth Pro", "", "")
        if p:
            self.path.setText(p)


class _SummaryPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self._wiz = wiz
        self.setTitle("All set")
        lay = QVBoxLayout(self)
        self.lbl = QLabel(); self.lbl.setWordWrap(True); lay.addWidget(self.lbl)

    def initializePage(self):
        w = self._wiz
        p1 = w.p1
        btns = []
        if p1.show_maps.isChecked(): btns.append("Google Maps")
        if p1.show_sv.isChecked(): btns.append("Street View")
        if p1.show_fly.isChecked(): btns.append("Open in Earth")
        if p1.show_send.isChecked(): btns.append("Export & send to Earth")
        path = w.p2.path.text().strip()
        self.lbl.setText(
            f"Toolbar buttons: {', '.join(btns) or 'none (all hidden)'}<br>"
            f"Earth target: {w.p2.target.currentText()}<br>"
            f"Earth Pro: {path or 'not set (Earth Web hand-off will be used)'}<br>"
            f"Export: {w.p2.fmt.currentText()}, up to {w.p2.cap.value():,} features<br><br>"
            "Click Finish to save.")


class SetupWizard(QWizard):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lazy Earth & Maps - Setup")
        self._s = settings
        self.p1, self.p2 = _ProfilePage(settings), _EarthPage(settings)
        self.addPage(self.p1); self.addPage(self.p2); self.addPage(_SummaryPage(self))
        self.accepted.connect(self._save)

    def _save(self):
        s = self._s
        s.set("show_maps", self.p1.show_maps.isChecked())
        s.set("show_streetview", self.p1.show_sv.isChecked())
        s.set("show_earth_fly", self.p1.show_fly.isChecked())
        s.set("show_earth_send", self.p1.show_send.isChecked())
        s.set("maps_basemap", self.p1.basemap.currentData())
        s.set("earth_target", self.p2.target.currentData())
        s.set("earth_pro_path", self.p2.path.text().strip())
        s.set("earth_tilt", self.p2.tilt.value())
        s.set("export_format", self.p2.fmt.currentData())
        s.set("feature_cap", self.p2.cap.value())
        s.set("include_attrs", self.p2.attrs.isChecked())
        s.set("open_folder_on_web", self.p2.folder.isChecked())
        s.set("label_fields", self.p2.labels.text().strip() or "name,title,label,id")
        s.set("first_run_done", True)
