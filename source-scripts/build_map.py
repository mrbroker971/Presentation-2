"""Build a stylised, rotated SVG map of Dubai from OpenStreetMap extracts.

Outputs an <svg> fragment with layers: land, water, roads, centres, key areas,
landmarks, labels. Colours come from CSS variables in deck.css.
"""
import json, math, os, sys
from shapely.geometry import LineString, Polygon, MultiPolygon, Point, box, mapping
from shapely.ops import linemerge, unary_union, split
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'map.svg')

LAT0, LON0 = 25.12, 55.20
K = 1000.0  # units per degree before fit
COS = math.cos(math.radians(LAT0))


def proj(lon, lat):
    return ((lon - LON0) * COS * K, -(lat - LAT0) * K)


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None

# ---------- coastline -> land ----------
coast = load('coast.json')
lines = [LineString([proj(p['lon'], p['lat']) for p in e['geometry']]) for e in coast['elements'] if e['type'] == 'way']
merged = linemerge(lines)
geoms = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
rings = [g for g in geoms if g.is_ring]
opened = sorted([g for g in geoms if not g.is_ring], key=lambda g: -g.length)

# rotation so the coast runs horizontally, sea on top
a = proj(55.02, 24.99); b = proj(55.32, 25.28)
ANG = -math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))  # degrees to rotate (ccw positive in shapely)

frame = box(-700, -700, 700, 700)
# extend the open mainland coastline far beyond the frame so it splits it cleanly
_ext = []
for g in geoms:
    if g.is_ring:
        _ext.append(g); continue
    c = list(g.coords)
    if g.length > 2000:  # mainland
        c = [proj(55.95, 25.95)] + c + [proj(54.35, 24.45)] if c[0][1] < c[-1][1] else [proj(54.35, 24.45)] + c + [proj(55.95, 25.95)]
    _ext.append(LineString(c))
geoms = _ext
from shapely.ops import polygonize, nearest_points
from shapely.strtree import STRtree
coast_all = unary_union([g for g in geoms]).intersection(frame)
faces = list(polygonize(unary_union([frame.boundary, coast_all])))
segs = []
for g in geoms:
    c = list(g.coords)
    for i in range(len(c) - 1):
        segs.append(LineString([c[i], c[i + 1]]))
tree = STRtree(segs)
def is_land(pt):
    seg = segs[tree.nearest(pt)]
    (px, py), (qx, qy) = seg.coords
    cross = (qx - px) * (pt.y - py) - (qy - py) * (pt.x - px)
    return cross < 0  # y axis is flipped, so OSM "land on the left" becomes negative cross
land = unary_union([f for f in faces if f.area > 0.0001 and is_land(f.representative_point())])
print('sea test (should be False):', is_land(Point(proj(55.10, 25.25))), ' land test (True):', is_land(Point(proj(55.30, 25.10))))
islands = [Polygon(r.coords).buffer(0) for r in rings]
land = unary_union([land] + [i for i in islands if not land.contains(i.representative_point())])
# Dubai Islands = offshore islands in front of Deira
di_box = Polygon([proj(55.255, 25.285), proj(55.345, 25.285), proj(55.345, 25.36), proj(55.255, 25.36)])
dubai_islands = unary_union([i for i in islands if di_box.contains(i.centroid) and i.area > 0.05])

# ---------- rotate everything ----------
ORIGIN = (0, 0)

def rot(g):
    return affinity.rotate(g, ANG, origin=ORIGIN)

def rpt(lon, lat):
    p = rot(Point(proj(lon, lat)))
    return p.x, p.y

land_r = rot(land)
di_r = rot(dubai_islands)

# view window: from Palm Jebel Ali to Dubai Islands along coast, inland to Expo/DLRC
keys = [(54.97, 24.985), (55.33, 25.355), (55.40, 25.075), (55.15, 24.945), (55.42, 25.17), (55.20, 25.27)]
xs, ys = zip(*[rpt(*k) for k in keys])
pad = 6
minx, maxx = min(xs) - pad, max(xs) + pad
# sea headroom on top for labels
miny, maxy = min(ys) - 10, max(ys) + pad
W, H = 1664, 700
FITW = W - 470  # leave room on the right for the legend
s = min(FITW / (maxx - minx), H / (maxy - miny))
cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

def tx(x, y):
    return (FITW / 2 + (x - cx) * s, H / 2 + (y - cy) * s)

view = box(*(lambda p0, p1: (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])))(
    (cx - FITW / 2 / s, cy - H / 2 / s), (cx + (W - FITW / 2) / s, cy + H / 2 / s))).buffer(4)


def path_of(geom, tol=0.0):
    if geom.is_empty:
        return ''
    if tol:
        geom = geom.simplify(tol / s, preserve_topology=True)
    out = []
    def ring(coords, close=True):
        pts = [tx(x, y) for x, y in coords]
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
        return d + ('Z' if close else '')
    if geom.geom_type == 'Polygon':
        geoms_ = [geom]
    elif geom.geom_type == 'MultiPolygon':
        geoms_ = list(geom.geoms)
    elif geom.geom_type in ('LineString', 'MultiLineString'):
        ls = [geom] if geom.geom_type == 'LineString' else list(geom.geoms)
        return ' '.join(ring(l.coords, False) for l in ls if len(l.coords) > 1)
    else:
        geoms_ = [g for g in getattr(geom, 'geoms', []) if g.geom_type in ('Polygon',)]
    for p in geoms_:
        out.append(ring(p.exterior.coords))
        for h in p.interiors:
            out.append(ring(h.coords))
    return ' '.join(out)

land_v = land_r.intersection(view)

# ---------- water (creek / canal) ----------
water_paths = []
w = load('water.json')
if w:
    polys = []
    for e in w['elements']:
        if e['type'] == 'way' and 'geometry' in e:
            pts = [proj(p['lon'], p['lat']) for p in e['geometry']]
            if len(pts) > 3 and pts[0] == pts[-1]:
                polys.append(Polygon(pts).buffer(0))
            elif e.get('tags', {}).get('waterway') == 'canal':
                polys.append(LineString(pts).buffer(0.06))
        if e['type'] == 'relation':
            for m in e.get('members', []):
                if m.get('role') == 'outer' and 'geometry' in m:
                    pts = [proj(p['lon'], p['lat']) for p in m['geometry']]
                    if len(pts) > 3 and pts[0] == pts[-1]:
                        polys.append(Polygon(pts).buffer(0))
    if polys:
        water = rot(unary_union(polys)).intersection(view)
        water_paths.append(path_of(water, 0.4))

# ---------- roads ----------
def roads(name, tol):
    r = load(name)
    if not r:
        return ''
    ls = [LineString([proj(p['lon'], p['lat']) for p in e['geometry']]) for e in r['elements'] if e['type'] == 'way' and len(e.get('geometry', [])) > 1]
    m = linemerge(ls)
    m = rot(m).intersection(view)
    return path_of(m, tol)

road_major = roads('roads1.json', 0.6)
road_minor = roads('roads2.json', 0.8)

# ---------- zones: whole city split into the 5 centres (schematic Voronoi) ----------
from shapely.geometry import MultiPoint
from shapely.ops import voronoi_diagram

seeds = {'1': (55.305, 25.262), '2': (55.270, 25.184), '3': (55.140, 25.080), '4': (55.152, 24.961), '5': (55.385, 25.121)}
seed_pts = {z: rot(Point(proj(*ll))) for z, ll in seeds.items()}
vor = voronoi_diagram(MultiPoint(list(seed_pts.values())), envelope=view.buffer(50))
cells = {}
for cell in vor.geoms:
    for z, p in seed_pts.items():
        if cell.contains(p):
            cells[z] = cell
GAP = 1.6 / s  # ~1.6 px gap between zones
land_main = land_v.buffer(0)
zones = {z: c.intersection(land_main).buffer(-GAP) for z, c in cells.items()}

badge = {'1': (55.350, 25.292), '2': (55.245, 25.150), '3': (55.190, 25.068), '4': (55.085, 24.985), '5': (55.445, 25.170)}
names = {'1': 'Deira и Bur Dubai', '2': 'Downtown и Business Bay', '3': 'Dubai Marina и JBR', '4': 'Expo City', '5': 'Dubai Silicon Oasis'}

dlrc_c = Point(proj(55.3845, 25.0905))
dlrc = rot(dlrc_c.buffer(9, quad_segs=3))
key = {'di': (di_r.buffer(0.15, join_style=1), '1'), 'dlrc': (dlrc, '5')}
key_anchor = {'di': (55.300, 25.318), 'dlrc': (55.3845, 25.0905)}

# icon glyphs, 24x24
ICONS = {
    'burj': '<path d="M12 .5 L12.9 8 L14.4 11.5 L15.6 23 L8.4 23 L9.6 11.5 L11.1 8 Z"/>',
    'sail': '<path d="M7 23 V2.5 H8.4 Q19.5 9 16.5 23 Z M9.6 6 V21 H14.8 Q16.6 11 9.6 6 Z" fill-rule="evenodd"/>',
    'atlantis': '<path d="M2.5 23 V11 H7 V6.5 H17 V11 H21.5 V23 H14 V17 Q12 13.5 10 17 V23 Z"/>',
    'plane': '<path d="M21 15.5v-2l-7.5-4.7V3.6a1.5 1.5 0 0 0-3 0v5.2L3 13.5v2l7.5-2.3v5L8.5 19.7v1.6L12 20.3l3.5 1v-1.6l-2-1.5v-5z"/>',
    'globe': '<path d="M12 2.5a9.5 9.5 0 1 0 0 19a9.5 9.5 0 1 0 0-19Zm0 1.6c1.6 1.7 2.6 4.6 2.6 7.9s-1 6.2-2.6 7.9c-1.6-1.7-2.6-4.6-2.6-7.9s1-6.2 2.6-7.9Zm-7.9 7.1h15.8v1.6H4.1Z" fill-rule="evenodd"/>',
    'wheel': '<path d="M12 2.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17Zm0 1.6a6.9 6.9 0 1 1 0 13.8a6.9 6.9 0 1 1 0-13.8Z M11.3 4.5h1.4v15h-1.4Z M4.5 10.3h15v1.4h-15Z M9 23h6l-3-3.5Z" fill-rule="evenodd"/>',
    'frame': '<path d="M5 2 H19 V23 H5 Z M8 5.5 V19 H16 V5.5 Z" fill-rule="evenodd"/>',
    'dome': '<path d="M2.5 21 Q12 1 21.5 21 Z M6.5 19 Q12 7.5 17.5 19 Z" fill-rule="evenodd"/><path d="M1.5 21h21v1.6h-21z"/>',
}
landmarks = [
    ('Burj Khalifa', 'burj', 55.2744, 25.1972, 'right'),
    ('Burj Al Arab', 'sail', 55.1853, 25.1412, 'above'),
    ('Atlantis', 'atlantis', 55.1171, 25.1304, 'above'),
    ('Ain Dubai', 'wheel', 55.1225, 25.0794, 'left'),
    ('Dubai Frame', 'frame', 55.3004, 25.2353, 'left'),
    ('Аэропорт DXB', 'plane', 55.3657, 25.2532, 'right'),
    ('Global Village', 'globe', 55.3080, 25.0718, 'below'),
    ('Expo 2020', 'dome', 55.1500, 24.9637, 'below'),
]
island_labels = [
    ('Palm Jumeirah', 55.150, 25.112),
    ('Palm Jebel Ali', 54.990, 25.000),
    ('The World', 55.172, 25.222),
]

out = []
out.append(f'<svg class="dmap" viewBox="0 0 {W} {H}" role="img" aria-label="Карта Дубая: пять городских центров 2040, Dubai Islands и DLRC">')
out.append('<defs>' + ''.join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONS.items()) + '</defs>')
out.append(f'<rect class="sea" x="0" y="0" width="{W}" height="{H}"/>')
out.append(f'<path class="land" fill-rule="evenodd" d="{path_of(land_v, 0.5)}"/>')
out.append('<g class="zones">')
for z in sorted(zones):
    out.append(f'<path class="zone centre z{z}" data-z="c{z}" fill-rule="evenodd" d="{path_of(zones[z], 0.5)}"/>')
out.append('</g>')
for wp in water_paths:
    out.append(f'<path class="water" fill-rule="evenodd" d="{wp}"/>')
if road_minor:
    out.append(f'<path class="road minor" pathLength="1" d="{road_minor}"/>')
if road_major:
    out.append(f'<path class="road major" pathLength="1" d="{road_major}"/>')
for name, lo, la in island_labels:
    x, y = tx(*rpt(lo, la))
    out.append(f'<text class="place" x="{x:.0f}" y="{y:.0f}">{name}</text>')
labels = {'di': 'Dubai Islands', 'dlrc': 'DLRC'}
offs = {'di': (-215, -2), 'dlrc': (-92, 7)}
out.append('<g class="hots">')
for z, (g, parent) in key.items():
    x, y = tx(*rpt(*key_anchor[z]))
    ox, oy = offs[z]
    out.append(f'<g class="zone hot" data-z="{z}" data-parent="c{parent}"><path pathLength="1" fill-rule="evenodd" d="{path_of(g.intersection(view), 0.25)}"/>'
               f'<circle class="ping" cx="{x:.1f}" cy="{y:.1f}" r="10"/><circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="7"/>'
               f'<text class="hotlabel" x="{x + ox:.1f}" y="{y + oy:.1f}">{labels[z]}</text></g>')
out.append('</g>')
out.append('<g class="marks">')
for name, icon, lo, la, pos in landmarks:
    x, y = tx(*rpt(lo, la))
    if not (0 < x < W and 0 < y < H):
        continue
    dx, dy, anchor = {'below': (0, 36, 'middle'), 'above': (0, -24, 'middle'), 'right': (24, 6, 'start'), 'left': (-24, 6, 'end')}[pos]
    out.append(f'<g class="mark"><circle class="mbg" cx="{x:.1f}" cy="{y:.1f}" r="16"/><use href="#i-{icon}" x="{x - 10:.1f}" y="{y - 10:.1f}" width="20" height="20"/>'
               f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}">{name}</text></g>')
out.append('</g>')
out.append('<g class="badges">')
for z in sorted(badge):
    x, y = tx(*rpt(*badge[z]))
    out.append(f'<g class="badge" data-z="c{z}"><circle cx="{x:.1f}" cy="{y:.1f}" r="19"/><text class="num" x="{x:.1f}" y="{y + 5:.1f}">0{z}</text>'
               f'<text class="bname" x="{x:.1f}" y="{y + 40:.1f}">{names[z]}</text></g>')
out.append('</g>')
out.append(f'<text class="sea-label" x="{FITW*0.45:.0f}" y="36">Персидский залив</text>')
out.append(f'<text class="credit" x="{W - 8}" y="{H - 8}">© OpenStreetMap contributors</text>')
out.append('</svg>')
svg = '\n'.join(out)
open(OUT, 'w').write(svg)
print('zones', {z: round(g.area) for z, g in zones.items()}, 'bytes', len(svg))
