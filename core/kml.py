# -*- coding: utf-8 -*-
# Lazy Earth & Maps - a QGIS plugin by Lazy by Design (Sheldon Willie)
# Derived from "Open Google Maps" by Harry King (GPL). See NOTICE.txt.
# Licensed under the GNU General Public License v2 or (at your option) any later version.
"""GeoJSON-like features -> KML/KMZ. Pure Python (testable without QGIS)."""
import re
import zipfile
from xml.sax.saxutils import escape

_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
DEFAULT_STYLE = {"fill": (255, 140, 0, 110), "stroke": (255, 110, 0, 255), "width": 2.0}


def _t(s):
    return escape(_BAD.sub("", str(s)))


def kml_color(rgba):
    r, g, b, a = [int(max(0, min(255, v))) for v in rgba]
    return f"{a:02x}{b:02x}{g:02x}{r:02x}"


def _c(seq):
    return " ".join(f"{p[0]:.7f},{p[1]:.7f},0" for p in seq)


def _ring(r, tag):
    return f"<{tag}><LinearRing><coordinates>{_c(r)}</coordinates></LinearRing></{tag}>"


def _poly(rings):
    if not rings:
        return ""
    s = "<Polygon><tessellate>1</tessellate>" + _ring(rings[0], "outerBoundaryIs")
    for r in rings[1:]:
        s += _ring(r, "innerBoundaryIs")
    return s + "</Polygon>"


def geometry_kml(g):
    """Return (kml_string, family) where family is point|line|polygon|mixed."""
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point":
        return f"<Point><coordinates>{_c([c])}</coordinates></Point>", "point"
    if t == "LineString":
        return f"<LineString><tessellate>1</tessellate><coordinates>{_c(c)}</coordinates></LineString>", "line"
    if t == "Polygon":
        return _poly(c), "polygon"
    parts, fams = [], set()
    if t == "MultiPoint":
        for p in c:
            s, f = geometry_kml({"type": "Point", "coordinates": p}); parts.append(s); fams.add(f)
    elif t == "MultiLineString":
        for p in c:
            s, f = geometry_kml({"type": "LineString", "coordinates": p}); parts.append(s); fams.add(f)
    elif t == "MultiPolygon":
        for p in c:
            s, f = geometry_kml({"type": "Polygon", "coordinates": p}); parts.append(s); fams.add(f)
    elif t == "GeometryCollection":
        for sub in g.get("geometries", []):
            s, f = geometry_kml(sub); parts.append(s); fams.add(f)
    else:
        return "", "none"
    parts = [p for p in parts if p]
    if not parts:
        return "", "none"
    fam = fams.pop() if len(fams) == 1 else "mixed"
    return "<MultiGeometry>" + "".join(parts) + "</MultiGeometry>", fam


def _style_xml(sid, fam, st):
    fill, stroke, w = st["fill"], st["stroke"], st["width"]
    x = f'<Style id="{sid}">'
    if fam in ("point", "mixed"):
        x += (f"<IconStyle><color>{kml_color(fill[:3] + (255,))}</color><scale>0.8</scale><Icon>"
              "<href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle>"
              "<LabelStyle><scale>0.8</scale></LabelStyle>")
    if fam in ("line", "polygon", "mixed"):
        col = stroke if fam != "line" else (stroke if stroke[3] else fill)
        x += f"<LineStyle><color>{kml_color(col)}</color><width>{w:.1f}</width></LineStyle>"
    if fam in ("polygon", "mixed"):
        x += f"<PolyStyle><color>{kml_color(fill)}</color><fill>1</fill><outline>1</outline></PolyStyle>"
    return x + "</Style>"


def build_kml(doc_name, layers, look_at=None, include_attrs=True):
    """layers: [{name, features:[{name, geometry, attrs:[(k,v)], style:{fill,stroke,width}}]}]"""
    styles, body, n = {}, [], 0
    for lyr in layers:
        body.append(f"<Folder><name>{_t(lyr['name'])}</name>")
        for f in lyr["features"]:
            gx, fam = geometry_kml(f["geometry"])
            if not gx:
                continue
            st = f.get("style") or DEFAULT_STYLE
            key = (fam, tuple(st["fill"]), tuple(st["stroke"]), round(st["width"], 1))
            if key not in styles:
                styles[key] = f"s{len(styles)}"
            ext = ""
            if include_attrs and f.get("attrs"):
                ext = "<ExtendedData>" + "".join(
                    f'<Data name="{_t(k).replace(chr(34), "&quot;")}"><value>{_t(v)}</value></Data>'
                    for k, v in f["attrs"]) + "</ExtendedData>"
            body.append(f"<Placemark><name>{_t(f['name'])}</name><styleUrl>#{styles[key]}</styleUrl>"
                        f"{ext}{gx}</Placemark>")
            n += 1
        body.append("</Folder>")
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{_t(doc_name)}</name>")
    if look_at:
        head += ("<LookAt><longitude>{lon:.7f}</longitude><latitude>{lat:.7f}</latitude>"
                 "<altitude>0</altitude><heading>0</heading><tilt>0</tilt><range>{rng:.0f}</range>"
                 "<altitudeMode>relativeToGround</altitudeMode></LookAt>").format(**look_at)
    head += "".join(_style_xml(sid, k[0], {"fill": k[1], "stroke": k[2], "width": k[3]})
                    for k, sid in styles.items())
    return head + "".join(body) + "</Document></kml>", n


def write_kml(path, kml_text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(kml_text)


def write_kmz(path, kml_text):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml_text.encode("utf-8"))
