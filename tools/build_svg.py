# Builds the README banner SVGs. Text is converted to glyph paths (no font loading),
# so they render identically on GitHub, in dark and light, whatever its CSP does to fonts.
import math, os, re
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = 'C:/Projets/Portofolio'
OUT = 'C:/Projets/shm0m/assets'  # fonts are read from the portfolio repo (ROOT)
os.makedirs(OUT, exist_ok=True)

def oklch(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_, m_, s_ = L + .3963377774 * a + .2158037573 * b, L - .1055613458 * a - .0638541728 * b, L - .0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    rgb = (4.0767416621 * l - 3.3077115913 * m + .2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s,
           -.0041960863 * l - .7034186147 * m + 1.7076147010 * s)
    f = lambda x: 12.92 * x if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055
    return '#' + ''.join('%02x' % round(min(max(f(c), 0), 1) * 255) for c in rgb)

# the portfolio's own tokens (light = original values, dark = the site's dark theme)
THEMES = {
    'light': dict(bg=oklch(.995, .002, 260), ink=oklch(.2, .006, 260), muted=oklch(.5, .006, 260),
                  line=oklch(.9, .004, 260), violet=oklch(.48, .17, 292)),
    'dark': dict(bg=oklch(.174, .01, 260), ink=oklch(.879, .01, 260), muted=oklch(.62, .01, 260),
                 line=oklch(.27, .01, 260), violet=oklch(.69, .17, 292)),
}

class Face:
    def __init__(self, path, prefix, wght=None):
        f = TTFont(path)
        if wght and 'fvar' in f:
            f = instancer.instantiateVariableFont(f, {'wght': wght})
        self.f, self.gs, self.cmap = f, f.getGlyphSet(), f.getBestCmap()
        self.upm, self.hmtx, self.prefix, self.used = f['head'].unitsPerEm, f['hmtx'], prefix, {}
        self.cap = f['OS/2'].sCapHeight

    def g(self, ch):
        return self.cmap.get(ord(ch))

    def adv(self, ch):
        g = self.g(ch)
        return self.hmtx[g][0] if g else self.upm // 2

    def ref(self, g):
        self.used[g] = 1
        return self.prefix + re.sub(r'[^A-Za-z0-9]', '_', g)

    def width(self, s, size, track=0):
        return sum(self.adv(c) + track * self.upm for c in s) * size / self.upm

    def run(self, s, x, y, size, fill, track=0):
        sc, cx, out = size / self.upm, 0, []
        for ch in s:
            g = self.g(ch)
            if g and not ch.isspace():
                out.append('<use href="#%s" x="%d"/>' % (self.ref(g), cx))
            cx += self.adv(ch) + track * self.upm
        return '<g fill="%s" transform="translate(%.1f %.1f) scale(%.5f)">%s</g>' % (fill, x, y, sc, ''.join(out))

    def defs(self):
        out = []
        for g in self.used:
            pen = SVGPathPen(self.gs, ntos=lambda v: str(round(v)))
            self.gs[g].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            out.append('<path id="%s" d="%s"/>' % (self.ref(g), pen.getCommands()))
        return ''.join(out)

def banner(theme):
    t = THEMES[theme]
    U = Face(ROOT + '/fonts/unbounded-600-800-latin.woff2', 'u', wght=800)
    A = Face(ROOT + '/fonts/anonymous-pro-400-latin.woff2', 'a')
    W, H = 1200, 352
    name, size, track = 'shaïma derouich', 84, -.02
    assert U.width(name, size, track) <= 1080, 'name overflows the card'
    base = 126 + U.cap * size / U.upm  # cap top sits 56px under the top rule
    right = 'paris, fr'
    parts = [
        A.run('open to a 6-month final-year internship · jan 2027', 60, 49, 15, t['muted']),
        A.run(right, 1140 - A.width(right, 15), 49, 15, t['muted']),
        '<rect x="60" y="70" width="1080" height="1" fill="%s"/>' % t['line'],
        U.run(name, 56, base, size, t['ink'], track),
        A.run('application security engineer · ai security · llm red teaming', 60, base + 58, 20, t['ink']),
        A.run('ece paris · meng cybersecurity · ai for security, and security for ai', 60, base + 90, 15, t['muted']),
        '<rect x="60" y="%.1f" width="1080" height="1" fill="%s"/>' % (base + 124, t['line']),
        A.run('shaima-drh.vercel.app', 60, base + 146, 13, t['violet']),
        A.run('github.com/shm0m', 1140 - A.width('github.com/shm0m', 13), base + 146, 13, t['muted']),
    ]
    title = 'Shaïma Derouich, application security engineer: AI security and LLM red teaming'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title><defs>%s%s</defs><rect x=".5" y=".5" width="%d" height="%d" rx="14" fill="%s" stroke="%s"/>%s</svg>'
            ) % (W, H, W, H, title, title, U.defs(), A.defs(), W - 1, H - 1, t['bg'], t['line'], ''.join(parts))

for theme in THEMES:
    p = '%s/banner-%s.svg' % (OUT, theme)
    open(p, 'w', encoding='utf-8').write(banner(theme))
    print(p, os.path.getsize(p) // 1024, 'KB')
