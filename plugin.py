# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
import os
import re
import tempfile
import time
import webbrowser

from qgis.PyQt.QtCore import QTimer, QUrl, Qt
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QApplication, QMenu
try:
    from qgis.PyQt.QtWidgets import QAction
except ImportError:  # Qt6 builds
    from qgis.PyQt.QtGui import QAction
from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject,
    QgsRasterLayer, QgsRectangle,
)
from qgis.gui import QgsMapToolEmitPoint

from .core import urls, kml
from .core.earth import detect_earth_pro, launch_earth_pro
from .exporter import export_layer, is_exportable
from .options import LazyOptionsFactory, LazySettingsDialog
from .settings import Settings

TITLE = "Lazy Earth & Maps"
MENU = "&Lazy Earth & Maps"
WGS84 = "EPSG:4326"


class _Fail(Exception):
    pass


class LazyEarthMapsPlugin:
    COVERAGE_NAME = "Google Street View Coverage"

    def __init__(self, iface):
        self.iface = iface
        self.dir = os.path.dirname(__file__)
        self.s = Settings()
        self.toolbar = None
        self.menu_actions = []
        self.pick_tool = None
        self.options_factory = None
        self._cov_action = None

    # ------------------------------------------------------------ GUI
    def _icon(self, name):
        p = os.path.join(self.dir, "img", name) if name else ""
        return QIcon(p) if os.path.exists(p) else QIcon()

    def _act(self, text, icon, slot, tip=""):
        a = QAction(self._icon(icon), text, self.iface.mainWindow())
        a.setToolTip(tip or text)
        a.triggered.connect(lambda _checked=False, f=slot: f())
        return a

    def initGui(self):
        self.pick_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.pick_tool.canvasClicked.connect(self._picked)
        self.options_factory = LazyOptionsFactory(self.s, self._icon("icon.png"), self._build)
        self.iface.registerOptionsWidgetFactory(self.options_factory)
        self._build()

    def _build(self):
        self._teardown()
        mw = self.iface.mainWindow()
        self.toolbar = self.iface.addToolBar(TITLE)
        self.toolbar.setObjectName("LazyEarthMapsToolbar")

        def add(action, toolbar=True):
            if toolbar:
                self.toolbar.addAction(action)
            # Add to both Plugins menu and Web menu for maximum discoverability
            self.iface.addPluginToMenu(TITLE, action)
            self.iface.addPluginToWebMenu(MENU, action)
            self.menu_actions.append(action)

        if self.s.get("show_maps"):
            m = QMenu(mw)
            for text, fn in (
                ("Roadmap", lambda: self.open_maps("roadmap")),
                ("Satellite", lambda: self.open_maps("satellite")),
                ("Terrain", lambda: self.open_maps("terrain")),
                ("Drop a pin at centre / selection", self.open_pin),
                ("Copy Google Maps link", self.copy_link),
            ):
                m.addAction(self._act(text, "", fn))
            self._maps_menu = m
            a = self._act("Google Maps (click = default style, hold = more)", "icon_maps.png",
                          lambda: self.open_maps(None),
                          "Open the current view (or selected features) in Google Maps")
            a.setMenu(m)
            add(a)

        if self.s.get("show_streetview"):
            sv_icon = "icon_pegman.png" if self.s.get("sv_icon_style") == "pegman" else "icon_streetview.png"
            a_sv = self._act("Street View — click a point on the map",
                             sv_icon, self.start_pick,
                             "Click this button then click any point on the map to open Street View there")
            add(a_sv)

        # Street View Coverage overlay action
        a_cov = QAction(self._icon("icon_coverage.png"), "Street View Coverage (toggle blue lines)", mw)
        a_cov.setToolTip("Toggle real-time Google Street View coverage lines on the map canvas")
        a_cov.setCheckable(True)
        a_cov.setChecked(self._is_coverage_visible())
        a_cov.triggered.connect(lambda chk: self.toggle_coverage(enable=chk))
        self._cov_action = a_cov
        add(a_cov, toolbar=self.s.get("show_coverage"))

        if self.s.get("show_earth_fly"):
            add(self._act("Open in Google Earth (view only, no export)", "icon_earth.png", self.earth_fly,
                          "Open the current view (or selected features) in Google Earth - no KML/KMZ file"))

        if self.s.get("show_earth_send"):
            m2 = QMenu(mw)
            for text, fn in (
                ("Selected features (or active layer if none selected)", lambda: self.send_to_earth("smart")),
                ("Whole active layer", lambda: self.send_to_earth("active")),
                ("Selected features only", lambda: self.send_to_earth("selected")),
                ("All visible vector layers", lambda: self.send_to_earth("visible")),
                ("View only - no export", self.earth_fly),
                ("Open export folder", self.open_export_folder),
            ):
                m2.addAction(self._act(text, "", fn))
            self._earth_menu = m2
            a2 = self._act("Export & send layer to Google Earth (hold = more)", "icon_send.png",
                           lambda: self.send_to_earth("smart"),
                           "Export selection / active layer as KMZ/KML and open it in Google Earth")
            a2.setMenu(m2)
            add(a2)

        # Settings action directly in Plugins and Web menus
        add(self._act("Settings...", "icon.png", self.open_settings,
                      "Configure Lazy Earth & Maps toolbar buttons, coverage, and export settings"),
            toolbar=False)

    def _teardown(self):
        for a in self.menu_actions:
            self.iface.removePluginMenu(TITLE, a)
            self.iface.removePluginWebMenu(MENU, a)
        self.menu_actions = []
        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

    def open_settings(self):
        """Open direct Settings dialog."""
        dlg = LazySettingsDialog(self.s, self._build, self.iface.mainWindow())
        dlg.exec()

    def unload(self):
        if self.options_factory is not None:
            self.iface.unregisterOptionsWidgetFactory(self.options_factory)
            self.options_factory = None
        try:
            if self.iface.mapCanvas().mapTool() is self.pick_tool:
                self.iface.mapCanvas().unsetMapTool(self.pick_tool)
        except Exception:
            pass
        self._teardown()

    # ------------------------------------------------------------ helpers
    def _msg(self, text, level=None, duration=6):
        self.iface.messageBar().pushMessage(TITLE, text, level if level is not None else Qgis.Info, duration)

    def _xf(self, crs):
        return QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem(WGS84),
                                      QgsProject.instance().transformContext())

    def _active_vector(self):
        l = self.iface.activeLayer()
        return l if is_exportable(l) else None

    def _view(self, prefer_selection=True):
        """Camera info in WGS84. Uses the selection extent when there is one."""
        canvas = self.iface.mapCanvas()
        ms = canvas.mapSettings()
        if not ms.hasValidSettings():
            raise _Fail("Map settings are invalid.")
        xf = self._xf(ms.destinationCrs())
        lyr = self._active_vector()
        if prefer_selection and lyr is not None and lyr.selectedFeatureCount() > 0:
            r = self._xf(lyr.crs()).transformBoundingBox(lyr.boundingBoxOfSelected())
            w, s, e, n = r.xMinimum(), r.yMinimum(), r.xMaximum(), r.yMaximum()
            lat, lon = (s + n) / 2.0, (w + e) / 2.0
            zoom = urls.zoom_for_bbox(w, s, e, n) if (e - w) + (n - s) > 1e-6 else 18.0
            rng = urls.earth_range_for_bbox(w, s, e, n) if (e - w) + (n - s) > 1e-6 else 400.0
            return dict(lat=lat, lon=lon, zoom=min(zoom, 19.0), range=rng, heading=0.0,
                        note=f"{lyr.selectedFeatureCount()} selected feature(s) in '{lyr.name()}'")
        c = xf.transform(canvas.center())
        dpi = ms.outputDpi() or 96.0
        height_m = canvas.scale() * (canvas.height() / dpi) * 0.0254
        return dict(lat=c.y(), lon=c.x(), zoom=urls.zoom_from_scale(canvas.scale(), c.y()),
                    range=urls.earth_range_for_height(height_m),
                    heading=(-canvas.rotation()) % 360.0, note="")

    def _safe(self, fn):
        try:
            fn()
        except _Fail as e:
            self._msg(str(e), Qgis.Warning, 5)
        except Exception as e:  # keep QGIS alive, report plainly
            self._msg(f"Unexpected error: {e}", Qgis.Critical, 8)

    # ------------------------------------------------------------ Google Maps & Street View
    def _maps_url(self, basemap=None):
        v = self._view()
        return urls.google_maps_url(v["lat"], v["lon"], v["zoom"], basemap or self.s.get("maps_basemap")), v

    def open_maps(self, basemap=None):
        def go():
            u, v = self._maps_url(basemap)
            webbrowser.open(u)
            if v["note"]:
                self._msg("Centred on " + v["note"], duration=3)
        self._safe(go)

    def copy_link(self):
        def go():
            u, _ = self._maps_url(None)
            QApplication.clipboard().setText(u)
            self._msg("Google Maps link copied to clipboard.", duration=3)
        self._safe(go)

    def open_pin(self):
        def go():
            v = self._view()
            webbrowser.open(urls.google_pin_url(v["lat"], v["lon"]))
        self._safe(go)

    # ------------------------------------------------------------ Street View Coverage
    def _get_coverage_layer(self):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == self.COVERAGE_NAME:
                return layer
        return None

    def _is_coverage_visible(self):
        lyr = self._get_coverage_layer()
        if not lyr or not lyr.isValid():
            return False
        node = QgsProject.instance().layerTreeRoot().findLayer(lyr.id())
        return node.isVisible() if node else False

    def toggle_coverage(self, enable=None, notify=True):
        lyr = self._get_coverage_layer()
        if enable is None:
            enable = not self._is_coverage_visible()

        if enable:
            if lyr is None or not lyr.isValid():
                uri = urls.google_streetview_coverage_xyz_uri()
                lyr = QgsRasterLayer(uri, self.COVERAGE_NAME, "wms")
                if lyr.isValid():
                    QgsProject.instance().addMapLayer(lyr, True)
                else:
                    if notify:
                        self._msg("Could not load Google Street View coverage tiles.", Qgis.Warning)
                    return
            else:
                node = QgsProject.instance().layerTreeRoot().findLayer(lyr.id())
                if node:
                    node.setItemVisibilityChecked(True)
            if self._cov_action:
                self._cov_action.setChecked(True)
            if notify:
                self._msg("Street View coverage overlay activated (blue lines show 360° coverage).", duration=4)
        else:
            if lyr:
                node = QgsProject.instance().layerTreeRoot().findLayer(lyr.id())
                if node:
                    node.setItemVisibilityChecked(False)
            if self._cov_action:
                self._cov_action.setChecked(False)
            if notify:
                self._msg("Street View coverage overlay hidden.", duration=3)

    def start_pick(self):
        if self.s.get("auto_show_coverage"):
            self.toggle_coverage(enable=True, notify=False)
        self.iface.mapCanvas().setMapTool(self.pick_tool)
        self._msg("Click anywhere on the map (or on a blue coverage line) to open Street View.", duration=4)

    def _picked(self, point, _button):
        def go():
            ms = self.iface.mapCanvas().mapSettings()
            p = self._xf(ms.destinationCrs()).transform(point)
            webbrowser.open(urls.google_streetview_url(p.y(), p.x()))
            self.iface.actionPan().trigger()
        self._safe(go)

    # ------------------------------------------------------------ Google Earth
    def earth_fly(self):
        def go():
            v = self._view()
            webbrowser.open(urls.google_earth_web_url(
                v["lat"], v["lon"], v["range"], self.s.get("earth_tilt"), v["heading"]))
            if v["note"]:
                self._msg("Flying to " + v["note"], duration=3)
        self._safe(go)

    def _export_dir(self):
        d = self.s.get("export_dir") or os.path.join(tempfile.gettempdir(), "LazyEarthMaps")
        os.makedirs(d, exist_ok=True)
        return d

    def open_export_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._export_dir()))

    def _layers_for(self, mode):
        act = self._active_vector()
        if mode == "visible" or (mode == "smart" and act is None):
            root = QgsProject.instance().layerTreeRoot()
            lyrs = [n.layer() for n in root.findLayers() if n.isVisible() and is_exportable(n.layer())]
            if not lyrs:
                raise _Fail("No visible vector layers to send.")
            return lyrs, False
        if act is None:
            raise _Fail("Select a vector layer in the Layers panel first.")
        if mode == "selected" and act.selectedFeatureCount() == 0:
            raise _Fail(f"No features selected in '{act.name()}'.")
        return [act], mode in ("selected", "smart")

    def send_to_earth(self, mode="smart"):
        def go():
            lyrs, sel_only = self._layers_for(mode)
            ms = self.iface.mapCanvas().mapSettings()
            cap, total_bb, layers, notes, trunc = self.s.get("feature_cap"), None, [], [], False
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                for l in lyrs:
                    left = cap - sum(len(x["features"]) for x in layers)
                    if left <= 0:
                        trunc = True
                        break
                    d, st = export_layer(l, sel_only, left, self.s.get("label_fields"), ms)
                    layers.append(d)
                    trunc = trunc or st["truncated"]
                    if st["skipped"]:
                        notes.append(f"{st['skipped']} skipped in '{l.name()}'")
                    if st["bbox"]:
                        b = st["bbox"]
                        total_bb = b if total_bb is None else (
                            min(total_bb[0], b[0]), min(total_bb[1], b[1]),
                            max(total_bb[2], b[2]), max(total_bb[3], b[3]))
            finally:
                QApplication.restoreOverrideCursor()
            if total_bb is None:
                raise _Fail("Nothing exportable: no features with valid geometry.")
            w, s_, e, n = total_bb
            look = {"lon": (w + e) / 2.0, "lat": (s_ + n) / 2.0,
                    "rng": urls.earth_range_for_bbox(w, s_, e, n)}
            base = layers[0]["name"] if len(layers) == 1 else "multiple_layers"
            doc = f"{base}" + (" (selection)" if sel_only and lyrs[0].selectedFeatureCount() else "")
            text, count = kml.build_kml(doc, layers, look, self.s.get("include_attrs"))
            ext = self.s.get("export_format")
            fname = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_")[:40] or "export"
            path = os.path.join(self._export_dir(), f"{fname}_{time.strftime('%Y%m%d_%H%M%S')}.{ext}")
            (kml.write_kmz if ext == "kmz" else kml.write_kml)(path, text)
            if not (os.path.exists(path) and os.path.getsize(path) > 0):
                raise _Fail("Export file was not written.")
            extra = []
            if trunc:
                extra.append(f"capped at {cap:,} features (raise it in Settings)")
            extra += notes
            self._handoff(path, look, count, "; ".join(extra))
        self._safe(go)

    def _handoff(self, path, look, count, extra):
        target = self.s.get("earth_target")
        exe = self.s.get("earth_pro_path") or detect_earth_pro()
        tail = f" ({extra})" if extra else ""
        if target in ("auto", "pro") and exe and launch_earth_pro(exe, path):
            self._msg(f"Sent {count:,} feature(s) to Google Earth Pro{tail}.", Qgis.Success, 6)
            return
        QApplication.clipboard().setText(path)
        webbrowser.open(urls.google_earth_web_url(look["lat"], look["lon"], look["rng"], 0, 0))
        if self.s.get("open_folder_on_web"):
            self.open_export_folder()
        self._msg(f"{count:,} feature(s) exported{tail}. Path copied. In Earth Web use "
                  "Open local KML editor > Open KML from device and pick the file.",
                  Qgis.Info, 20)
