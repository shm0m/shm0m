# Builds the README banner SVGs. Text is converted to glyph paths (no font loading),
# so they render identically on GitHub, in dark and light, whatever its CSP does to fonts.
# Also builds the violet "top languages by repo" card shown next to the GitHub stats card.
import collections, html, json, math, os, re, urllib.request
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
    W, H = 1200, 300
    name, size, track = 'shaïma', 140, -.02
    w = U.width(name, size, track)
    base = (H + U.cap * size / U.upm) / 2  # centers the cap height (the ascenders of h) vertically
    word = U.run(name, (W - w) / 2, base, size, t['ink'], track)  # before defs(): run() records the glyphs it needs
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Shaïma">'
            '<title>Shaïma</title><defs>%s</defs><rect x=".5" y=".5" width="%d" height="%d" rx="14" fill="%s" stroke="%s"/>%s</svg>'
            ) % (W, H, W, H, U.defs(), W - 1, H - 1, t['bg'], t['line'], word)

# the frame of the github / github_dark themes the stats card uses, so the two cards match side by side
CARD = {'light': dict(bg='#ffffff', line='#e4e2e2', title='#0366d6', text='#586069',
                      shades=((.45, .17), (.56, .15), (.67, .12), (.77, .09), (.86, .06))),
        'dark': dict(bg='#0d1117', line='#2e343b', title='#0366d6', text='#77909c',
                     shades=((.74, .16), (.63, .15), (.53, .13), (.44, .11), (.36, .09)))}

def repo_languages(user='shm0m', top=5):
    """primary language of each public repo, most common first (ties keep GitHub's order, like the original card)"""
    # shortcut: a snapshot taken when this script runs, rerun it after adding repos
    with urllib.request.urlopen('https://api.github.com/users/%s/repos?per_page=100&type=owner' % user) as r:
        counts = collections.Counter(x['language'] for x in json.load(r) if x['language'])
    if 'C++' in counts and 'C' in counts:
        # the user prefers C in C++'s slot: C keeps its own repo count, C++ is left out
        c = counts.pop('C')
        counts = collections.Counter({('C' if k == 'C++' else k): (c if k == 'C++' else n) for k, n in counts.items()})
    langs = counts.most_common(top)
    assert langs, 'no repo languages found'
    return langs

def languages(theme, langs):
    c = CARD[theme]
    total, a, parts = sum(n for _, n in langs), -math.pi / 2, []
    at = lambda r, t: '%.2f %.2f' % (230 + r * math.cos(t), 120 + r * math.sin(t))
    for i, ((name, n), (L, C)) in enumerate(zip(langs, c['shades'])):
        b = a + min(2 * math.pi * n / total, 2 * math.pi - 1e-4)  # a full circle arc would draw nothing
        big = int(b - a > math.pi)
        fill = oklch(L, C, 292)
        parts.append('<path d="M%s A60 60 0 %d 1 %s L%s A35 35 0 %d 0 %s Z" fill="%s" stroke="%s" stroke-width="2"/>'
                     % (at(60, a), big, at(60, b), at(35, b), big, at(35, a), fill, c['bg']))
        y = 58 + i * 25.2
        parts.append('<rect x="40" y="%.1f" width="14" height="14" fill="%s"/><text x="62" y="%.1f" fill="%s" font-size="14">%s</text>'
                     % (y, fill, y + 12, c['text'], html.escape(name)))
        a = b
    label = 'Top languages by repo: ' + ', '.join('%s (%d)' % (name, n) for name, n in langs)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200" role="img" aria-label="%s">'
            '<title>%s</title><style>*{font-family:\'Segoe UI\',Ubuntu,"Helvetica Neue",Sans-Serif}</style>'
            '<rect x="1" y="1" rx="5" ry="5" width="338" height="198" fill="%s" stroke="%s"/>'
            '<text x="30" y="40" fill="%s" font-size="22">Top Languages by Repo</text>%s</svg>'
            ) % (html.escape(label), html.escape(label), c['bg'], c['line'], c['title'], ''.join(parts))

langs = repo_languages()
for theme in THEMES:
    for name, svg in (('banner', banner(theme)), ('languages', languages(theme, langs))):
        p = '%s/%s-%s.svg' % (OUT, name, theme)
        open(p, 'w', encoding='utf-8').write(svg)
        print(p, os.path.getsize(p) // 1024, 'KB')
