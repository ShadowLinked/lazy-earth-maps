# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
"""QGIS vector layers -> feature dicts for core.kml (reprojected to EPSG:4326)."""
import json

from qgis.core import (
    NULL, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFillSymbol, QgsGeometry,
    QgsLineSymbol, QgsProject, QgsRectangle, QgsRenderContext, QgsVectorLayer, QgsWkbTypes,
)

from .core.kml import DEFAULT_STYLE

WGS84 = "EPSG:4326"
MAX_FIELDS = 60


def is_exportable(layer):
    try:
        return isinstance(layer, QgsVectorLayer) and layer.isSpatial()
    except Exception:
        return False


def pick_label_field(layer, priority):
    names = {f.name().lower(): f.name() for f in layer.fields()}
    for want in [p.strip().lower() for p in priority.split(",") if p.strip()]:
        if want in names:
            return names[want]
    for f in layer.fields():
        if f.typeName().lower() in ("string", "text", "varchar"):
            return f.name()
    return None


def _val(v):
    if v is None or v == NULL:
        return ""
    return str(v)


def _style(sym):
    if sym is None:
        return DEFAULT_STYLE
    try:
        is_fill, is_line = isinstance(sym, QgsFillSymbol), isinstance(sym, QgsLineSymbol)
        c = sym.color()
        op = sym.opacity()
        fill = (c.red(), c.green(), c.blue(), int(c.alpha() * op * (0.55 if is_fill else 1.0)))
        stroke, width = (c.red(), c.green(), c.blue(), int(c.alpha() * op)), 2.0
        if is_line:
            width = max(1.0, min(8.0, sym.width() * 3.78))
        if is_fill and sym.symbolLayerCount():
            sl = sym.symbolLayer(0)
            if hasattr(sl, "strokeColor"):
                sc = sl.strokeColor()
                stroke = (sc.red(), sc.green(), sc.blue(), sc.alpha())
            if hasattr(sl, "strokeWidth"):
                width = max(1.0, min(6.0, sl.strokeWidth() * 3.78))
        return {"fill": fill, "stroke": stroke, "width": width}
    except Exception:
        return DEFAULT_STYLE


def export_layer(layer, selected_only, cap, label_priority, ctx_settings):
    """Return (layer_dict, stats). stats: used, skipped, truncated, bbox(w,s,e,n) or None."""
    layer_crs = layer.crs()
    is_wgs84 = layer_crs.authid().upper() == WGS84 or layer_crs == QgsCoordinateReferenceSystem(WGS84)
    xf = None if is_wgs84 else QgsCoordinateTransform(
        layer_crs, QgsCoordinateReferenceSystem(WGS84),
        QgsProject.instance().transformContext()
    )
    use_sel = selected_only and layer.selectedFeatureCount() > 0
    feats = layer.getSelectedFeatures() if use_sel else layer.getFeatures()
    label = pick_label_field(layer, label_priority)
    fields = layer.fields()
    names = [f.name() for f in fields][:MAX_FIELDS]
    indices = [fields.indexOf(n) for n in names]
    label_idx = fields.indexOf(label) if label else -1

    renderer, ctx = layer.renderer(), None
    if renderer is not None:
        try:
            ctx = QgsRenderContext.fromMapSettings(ctx_settings)
            renderer.startRender(ctx, fields)
        except Exception:
            renderer = None

    out, skipped, truncated, bbox = [], 0, False, None
    try:
        for f in feats:
            if len(out) >= cap:
                truncated = True
                break
            g = f.geometry()
            if g is None or g.isNull() or g.isEmpty():
                skipped += 1
                continue
            try:
                g = QgsGeometry(g)
                # Drop 3D / Z value if present so elevations don't corrupt 2D KML
                if QgsWkbTypes.hasZ(g.wkbType()):
                    try:
                        g.get().dropZValue()
                    except Exception:
                        pass
                # Transform to EPSG:4326 if not already WGS84
                if xf is not None and g.transform(xf) != 0:
                    skipped += 1
                    continue

                # Fast path for single point geometries (bypasses JSON parser)
                if g.type() == QgsWkbTypes.PointGeometry and not g.isMultipart():
                    pt = g.asPoint()
                    gj = {"type": "Point", "coordinates": [round(pt.x(), 7), round(pt.y(), 7)]}
                else:
                    gj = json.loads(g.asJson(7))

                bb = g.boundingBox()
            except Exception:
                skipped += 1
                continue

            bbox = QgsRectangle(bb) if bbox is None else bbox
            bbox.combineExtentWith(bb)
            sym = None
            if renderer is not None:
                try:
                    sym = renderer.symbolForFeature(f, ctx)
                except Exception:
                    sym = None

            feat_name = _val(f.attribute(label_idx)) if label_idx >= 0 else ""
            out.append({
                "name": feat_name or f"{layer.name()} #{f.id()}",
                "geometry": gj,
                "attrs": [(names[i], _val(f.attribute(idx))) for i, idx in enumerate(indices) if idx >= 0],
                "style": _style(sym),
            })
    finally:
        if renderer is not None and ctx is not None:
            try:
                renderer.stopRender(ctx)
            except Exception:
                pass
    stats = {"used": len(out), "skipped": skipped, "truncated": truncated, "selection": use_sel,
             "bbox": (bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()) if bbox else None}
    return {"name": layer.name(), "features": out}, stats
