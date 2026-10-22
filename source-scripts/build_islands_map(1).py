"""Build the interactive Dubai Islands (A–E) SVG map from OSM extracts.

Inputs (from the OSM scratch folder): coast.json, roads1.json, di_islands.json
Output: SVG fragment printed to the given path.
"""
import json, math, sys, os
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import polygonize, unary_union, linemerge
from shapely.strtree import STRtree

SRC = sys.argv[1]
OUT = sys.argv[2]
J = lambda n: json.load(open(os.path.join(SRC, n)))

W, H, FITW = 1664, 770, 1180
LAT0, LAT1 = 25.2755, 25.3595
S = H / (LAT1 - LAT0)
COS = math.cos(math.radians(25.31))
LON0 = 55.312 - 560 / (S * COS)

def tx(lon, lat):
    return ((lon - LON0) * S * COS, (LAT1 - lat) * S)

view = box(LON0, LAT0 - 0.01, LON0 + W / (S * COS), LAT1 + 0.01)

# mainland land: faces of (coast lines + view boundary) that lie left of the coastline
coast = J('coast.json')
lines = [LineString([(p['lon'], p['lat']) for p in e['geometry']]) for e in coast['elements'] if e['type'] == 'way']
merged = linemerge(lines)
geoms = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
open_lines = [g for g in geoms if not g.is_ring]
clip = [g.intersection(view) for g in open_lines]
clip = [g for g in clip if not g.is_empty]
faces = list(polygonize(unary_union(clip + [view.boundary])))
segs = []
for g in open_lines:
    c = list(g.coords)
    segs += [LineString([c[i], c[i + 1]]) for i in range(len(c) - 1)]
tree = STRtree(segs)

def is_land(pt):
    (px, py), (qx, qy) = segs[tree.nearest(pt)].coords
    return (qx - px) * (pt.y - py) - (qy - py) * (pt.x - px) > 0

mainland = unary_union([f for f in faces if is_land(f.representative_point())])
# other small islands (rings) in view, excluding Dubai Islands themselves
isl = {k: shape(v) for k, v in J('di_islands.json').items()}
di_all = unary_union(list(isl.values())).buffer(0.0005)
others = [Polygon(g.coords).buffer(0) for g in geoms if g.is_ring]
others = [o for o in others if view.contains(o.centroid) and not di_all.intersects(o)]
land = unary_union([mainland] + others)

def path(g, tol=0.00004):
    g = g.simplify(tol, preserve_topology=True)
    out = []
    polys = [g] if g.geom_type == 'Polygon' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']
    for p in polys:
        for ring in [p.exterior] + list(p.interiors):
            pts = [tx(x, y) for x, y in ring.coords]
            out.append('M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z')
    return ' '.join(out)

def lpath(g, tol=0.00006):
    g = g.simplify(tol)
    ls = [g] if g.geom_type == 'LineString' else [x for x in getattr(g, 'geoms', []) if x.geom_type == 'LineString']
    return ' '.join('M' + ' L'.join('%.1f %.1f' % tx(x, y) for x, y in l.coords) for l in ls if len(l.coords) > 1)

roads = J('roads1.json')
rl = [LineString([(p['lon'], p['lat']) for p in e['geometry']]) for e in roads['elements'] if e['type'] == 'way' and len(e.get('geometry', [])) > 1]
road = unary_union(rl).intersection(view)

ICONS = {
    'mall': '<path d="M5 8h14l-1.2 13.5H6.2Z M8.5 8V6.5a3.5 3.5 0 0 1 7 0V8h-1.6V6.5a1.9 1.9 0 0 0-3.8 0V8Z" fill-rule="evenodd"/>',
    'marina': '<path d="M11.2 2.5h1.6v2.2a2.4 2.4 0 1 1-1.6 0Zm.8 3.3a.9.9 0 1 0 0 .01ZM11.2 9h1.6v10.4c2.6-.3 4.6-2 5.3-4.4l-1.8.6.7-3.8 2.9 2.6-1.7-.1C17.9 18 15.3 21 12 21s-5.9-3-6.9-6.7l-1.7.1 2.9-2.6.7 3.8-1.8-.6c.7 2.4 2.7 4.1 5.3 4.4Z M8 9h8v1.5H8Z" fill-rule="evenodd"/>',
    'beach': '<path d="M12 3a9 9 0 0 1 9 8H3a9 9 0 0 1 9-8Z M11.2 11h1.6v9h-1.6Z M3 20.5h18V22H3Z"/>',
    'golf': '<path d="M7 2h1.6v17H7Z M8.6 2.5 18 6.5l-9.4 4Z M3 21c2-2.2 16-2.2 18 0Z"/>',
    'park': '<path d="M12 2c3.6 0 6 2.6 6 5.8 0 2.8-2 5-4.6 5.4V20h-2.8v-6.8C8 12.8 6 10.6 6 7.8 6 4.6 8.4 2 12 2Z M5 20h14v1.6H5Z"/>',
    'sport': '<path d="M12 2.5a9.5 9.5 0 1 0 0 19a9.5 9.5 0 1 0 0-19Zm0 1.7a7.8 7.8 0 0 1 5.2 2L14.9 8.9H9.1L6.8 6.2A7.8 7.8 0 0 1 12 4.2Zm-6.2 3 2.3 2.7-1.8 5.4-2.5.3a7.8 7.8 0 0 1 2-8.4Zm12.4 0a7.8 7.8 0 0 1 2 8.4l-2.5-.3-1.8-5.4Zm-9 3.4h5.6l1.7 5.1L12 18.6l-4.5-3Z" fill-rule="evenodd"/>',
    'villa': '<path d="M12 3 2 11h2.5v10h6v-6h3v6h6V11H22Z"/>',
    'hotel': '<path d="M4 3h16v18h-6v-4h-4v4H4Zm3 3v2.2h2.4V6Zm4 0v2.2h2V6Zm4 0v2.2h2.2V6ZM7 10.2v2.2h2.4v-2.2Zm4 0v2.2h2v-2.2Zm4 0v2.2h2.2v-2.2Z" fill-rule="evenodd"/>',
}
marks = [
    ('mall', 'Главный ТЦ', 55.300, 25.2885, 'A'),
    ('marina', 'Центральная марина', 55.2985, 25.3005, 'A'),
    ('hotel', 'Курорты на пляже', 55.326, 25.3155, 'B'),
    ('beach', 'Пляжи', 55.3175, 25.3065, 'B'),
    ('golf', 'Гольф 18 лунок', 55.302, 25.338, 'C'),
    ('park', 'Oasis Park', 55.3125, 25.326, 'C'),
    ('sport', 'Спортивный клуб', 55.2875, 25.309, 'D'),
    ('villa', 'Виллы у воды', 55.3375, 25.3135, 'E'),
]
labels = {'A': (55.311, 25.2905), 'B': (55.3205, 25.3215), 'C': (55.293, 25.3465), 'D': (55.2885, 25.3015), 'E': (55.3435, 25.3245)}
zcls = {'A': 'z1', 'B': 'z3', 'C': 'z4', 'D': 'z2', 'E': 'z5'}
garda = (55.3072, 25.2985)

o = [f'<svg class="dmap imap" viewBox="0 0 {W} {H}" role="img" aria-label="Карта Dubai Islands: пять островов A–E">']
o.append('<defs>' + ''.join(f'<symbol id="ii-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONS.items()) + '</defs>')
o.append(f'<rect class="sea" width="{W}" height="{H}"/>')
o.append(f'<path class="land" fill-rule="evenodd" d="{path(land.intersection(view))}"/>')
o.append(f'<path class="road major" d="{lpath(road)}"/>')
for name, lo, la in [('Deira', 55.325, 25.279), ('Al Mamzar', 55.352, 25.3005), ('Dubai Creek', 55.2955, 25.278), ('Port Rashid', 55.272, 25.279)]:
    x, y = tx(lo, la)
    o.append(f'<text class="place" x="{x:.0f}" y="{y:.0f}">{name}</text>')
o.append('<g class="zones">')
for k in 'ABCDE':
    o.append(f'<path class="zone centre {zcls[k]}" data-z="i{k}" fill-rule="evenodd" d="{path(isl[k])}"/>')
o.append('</g>')
o.append('<g class="badges">')
for k, (lo, la) in labels.items():
    x, y = tx(lo, la)
    o.append(f'<g class="badge" data-z="i{k}"><circle cx="{x:.1f}" cy="{y:.1f}" r="22"/><text class="num big" x="{x:.1f}" y="{y + 7:.1f}">{k}</text></g>')
o.append('</g>')
o.append('<g class="imarks">')
for icon, name, lo, la, k in marks:
    x, y = tx(lo, la)
    o.append(f'<g class="imark" data-z="i{k}"><circle cx="{x:.1f}" cy="{y:.1f}" r="15"/><use href="#ii-{icon}" x="{x - 9:.1f}" y="{y - 9:.1f}" width="18" height="18"/><text x="{x:.1f}" y="{y + 32:.1f}">{name}</text></g>')
o.append('</g>')
x, y = tx(*garda)
o.append(f'<g class="gpin"><circle class="ping" cx="{x:.1f}" cy="{y:.1f}" r="9"/><circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="8"/>'
         f'<text x="{x + 16:.1f}" y="{y + 6:.1f}">Villa del Garda</text></g>')
o.append(f'<text class="sea-label" x="{tx(55.272, 25.336)[0]:.0f}" y="{tx(55.272, 25.336)[1]:.0f}">Персидский залив</text>')
o.append(f'<text class="credit" x="{W - 8}" y="{H - 8}">© OpenStreetMap contributors</text>')
o.append('</svg>')
open(OUT, 'w').write('\n'.join(o))
print('ok', len('\n'.join(o)))
