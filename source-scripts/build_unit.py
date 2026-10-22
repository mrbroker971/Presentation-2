# Builds the interactive plan of unit 201 (schematic, redrawn from the developer plan) and injects it into index.html
import re
ROOMS = [  # id, label lines, label x,y, polygon
 ("bath", ["Ванная"], 181, 262, "100,200 262,200 262,305 100,305"),
 ("st", ["Кладовая"], 313, 262, "262,200 365,200 365,305 262,305"),
 ("dress", ["Гардеробная"], 255, 347, "190,305 320,305 320,365 190,365"),
 ("bed", ["Спальня"], 230, 455, "50,330 100,330 100,305 190,305 190,365 320,365 320,530 50,530"),
 ("pr", ["Гостевой", "санузел"], 540, 108, "450,35 630,35 647,135 450,135"),
 ("kit", ["Кухня и столовая"], 512, 222, "365,200 385,135 647,135 685,340 365,340"),
 ("liv", ["Гостиная"], 470, 460, "320,305 365,305 365,340 685,340 720,530 320,530"),
 ("balc", ["Балкон"], 400, 625, "50,530 740,530 745,668 Q400,705 50,690"),
]
def poly(p):
    if "Q" in p:
        a, q = p.split(" Q"); pts = a.split(); return "M" + " L".join(pts) + " Q" + q + " Z"
    return "M" + " L".join(p.split()) + " Z"
s = []
s.append('<svg class="uplan" viewBox="20 10 760 710" role="img" aria-label="Планировка юнита 201">')
for rid, lines, x, y, p in ROOMS:
    s.append(f'<path class="room" data-r="{rid}" d="{poly(p)}"/>')
# furniture (decor)
F = []
F += ['<rect x="62" y="372" width="150" height="132" rx="6"/>', '<rect x="68" y="380" width="30" height="54" rx="5"/>', '<rect x="68" y="442" width="30" height="54" rx="5"/>',
      '<rect x="62" y="342" width="34" height="24" rx="3"/>', '<rect x="62" y="508" width="34" height="18" rx="3"/>']
F += [f'<line x1="{x}" y1="311" x2="{x}" y2="327"/>' for x in (222, 254, 286)] + ['<rect x="194" y="311" width="122" height="16" rx="2"/>']
F += ['<ellipse cx="135" cy="236" rx="15" ry="20"/>', '<rect x="122" y="212" width="26" height="10" rx="3"/>', '<rect x="196" y="212" width="50" height="30" rx="4"/>', '<circle cx="221" cy="227" r="8"/>']
F += ['<ellipse cx="612" cy="74" rx="13" ry="18"/>', '<rect x="600" y="46" width="24" height="9" rx="3"/>', '<rect x="462" y="44" width="40" height="24" rx="4"/>', '<circle cx="482" cy="56" r="6"/>']
F += ['<path d="M454,141 L640,141 L676,330 L636,330 L604,178 L454,178 Z"/>'] + [f'<circle cx="{cx}" cy="{cy}" r="7"/>' for cx, cy in ((482, 152), (502, 152), (482, 167), (502, 167))]
F += ['<rect x="614" y="200" width="22" height="36" rx="4"/>']
F += ['<circle cx="480" cy="282" r="34"/>'] + [f'<rect x="{x-11}" y="{y-11}" width="22" height="22" rx="6" transform="rotate(45 {x} {y})"/>' for x, y in ((446, 248), (514, 248), (446, 316), (514, 316))]
F += ['<path d="M618,372 Q700,420 650,512 L626,500 Q666,428 604,392 Z"/>', '<circle cx="586" cy="446" r="24"/>']
F += [f'<rect x="{x}" y="556" width="30" height="96" rx="5"/>' for x in (70, 112, 154, 196, 238)]
s.append('<g class="furn">' + "".join(F) + '</g>')
s.append('<rect class="pool" data-r="balc" x="588" y="542" width="138" height="72" rx="6"/>')
s.append('<text class="pool-t" x="657" y="583">бассейн</text>')
# walls
s.append('<path class="wall" d="M394,135 L385,135 L365,200 L100,200 L100,330 L50,330 L50,530 L720,530 L630,35 L450,35 L450,135 L442,135"/>')
# entrance door (position taken from the door swing on the developer plan)
s.append('<g class="entry" data-r="entry"><path class="leaf" d="M442,135 L442,183"/><path class="swing" d="M394,135 A48,48 0 0 0 442,183"/>'
         '<path class="arrow" d="M418,76 L418,124 M408,112 L418,126 L428,112"/><text x="404" y="104" style="text-anchor:end">Вход</text></g>')
W = ["262,200 262,305", "100,305 145,305", "185,305 262,305", "262,305 325,305", "358,305 365,305", "365,200 365,305",
     "320,305 320,368", "320,412 320,530", "450,135 540,135", "590,135 647,135"]
s.append('<g class="iwall">' + "".join(f'<polyline points="{w}"/>' for w in W) + '</g>')
s.append('<path class="balc-edge" d="M50,530 L740,530 L745,668 Q400,705 50,690 Z"/>')
s.append('<g class="glass">' + "".join(f'<line x1="{a}" y1="530" x2="{b}" y2="530"/>' for a, b in ((60, 310), (330, 712))) + '</g>')
# exits to balcony
s.append('<g class="exits">' + "".join(f'<path d="M{x},508 L{x},560 M{x-10},548 L{x},562 L{x+10},548"/>' for x in (185, 470)) + '</g>')
for rid, lines, x, y, p in ROOMS:
    dy = -12 * (len(lines) - 1)
    t = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else 24}">{l}</tspan>' for i, l in enumerate(lines))
    s.append(f'<text class="rl" data-r="{rid}" x="{x}" y="{y + dy}">{t}</text>')
s.append('</svg>')
svg = "\n".join(s)
ITEMS = [
 ("liv bed balc", "Выход на балкон", "Гостиная и спальня выходят на один длинный балкон с плунж бассейном", True),
 ("liv", "Гостиная", "Светлая гостиная с панорамным остеклением и выходом на балкон", False),
 ("kit", "Кухня и столовая", "Встроенная кухня с техникой и обеденный стол на четверых", False),
 ("bed", "Спальня", "Двуспальная кровать, окно в пол и свой выход на балкон", False),
 ("dress", "Гардеробная", "Встроенная гардеробная прямо при спальне", False),
 ("bath", "Ванная", "Основной санузел рядом со спальней", False),
 ("entry pr", "Вход", "Вход из общего коридора, гостевой санузел сразу у двери", False),
 ("pr", "Гостевой санузел", "Отдельный санузел для гостей у входа", False),
 ("st", "Кладовая", "Место для хранения вещей", False),
 ("balc", "Балкон с бассейном", "14,9 м², собственный плунж бассейн и шезлонги", False),
]
lg = '<div class="plegend"><p class="pl-title">Планировка</p><ul>' + "".join(
    f'<li data-r="{r}" data-desc="{d}"{" class=\"key\"" if k else ""}>{n}</li>' for r, n, d, k in ITEMS) + '</ul><p class="pl-desc">Наведите на комнату или пункт списка</p></div>'
h = open("index.html").read()
h = re.sub(r'<figure class="plan">.*?</figure>', '<figure class="plan">\n' + svg + '\n</figure>', h, count=1, flags=re.S)
h = re.sub(r'<figure class="unit-photo"[^>]*></figure>|<div class="plegend">.*?</div>', lg, h, count=1, flags=re.S)
BG = {"liv": "v", "kit": "r", "bed": "v", "dress": "r", "bath": "r", "balc": "v"}
def bgel(k, kind):
    on = ' class="on"' if k == "liv" else ""
    if kind == "v":
        return f'<video data-bg="{k}"{on} src="../assets/garda/v-{k}.mp4" poster="../assets/garda/v-{k}.jpg" muted loop playsinline preload="{"auto" if k == "liv" else "metadata"}"></video>'
    return f'<i data-bg="{k}"{on} style="background-image:url(../assets/garda/r-{k}.jpg)"></i>'
bg = '<div class="ubg">' + "".join(bgel(k, v) for k, v in BG.items()) + '</div>'
h = re.sub(r'<section class="(?:light|dark) unit-slide">\s*(?:<div class="ubg">.*?</div>\s*)?<div class="slide">', '<section class="dark unit-slide">\n  ' + bg + '\n  <div class="slide">', h, count=1, flags=re.S)
open("index.html", "w").write(h)
print("ok", len(svg))
