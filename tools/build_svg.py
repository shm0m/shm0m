# Builds the README banner/footer SVGs. Text is converted to glyph paths (no font loading),
# so they render identically on GitHub, in dark and light, whatever its CSP does to fonts.
import math, os, re, random, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

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
                  line=oklch(.9, .004, 260), violet=oklch(.48, .17, 292), hex=oklch(.4, .04, 296)),
    'dark': dict(bg=oklch(.174, .01, 260), ink=oklch(.879, .01, 260), muted=oklch(.62, .01, 260),
                 line=oklch(.27, .01, 260), violet=oklch(.69, .17, 292), hex=oklch(.77, .04, 296)),
}

class Face:
    def __init__(self, path, prefix, wght=None):
        f = TTFont(path)
        if wght and 'fvar' in f:
            f = instancer.instantiateVariableFont(f, {'wght': wght})
        self.f, self.gs, self.cmap = f, f.getGlyphSet(), f.getBestCmap()
        self.upm, self.hmtx, self.prefix, self.used = f['head'].unitsPerEm, f['hmtx'], prefix, {}
        os2 = f['OS/2']
        self.xh, self.cap = os2.sxHeight, os2.sCapHeight

    def g(self, ch):
        return self.cmap.get(ord(ch))

    def adv(self, ch):
        g = self.g(ch)
        return self.hmtx[g][0] if g else self.upm // 2

    def ref(self, g):
        self.used[g] = 1
        return self.prefix + re.sub(r'[^A-Za-z0-9]', '_', g)

    def bounds(self, ch):
        bp = BoundsPen(self.gs); self.gs[self.g(ch)].draw(bp); return bp.bounds

    def width(self, s, size, track=0):
        return sum(self.adv(c) + track * self.upm for c in s) * size / self.upm

    def run(self, s, x, y, size, fill, track=0, attrs=''):
        sc, cx, out = size / self.upm, 0, []
        for ch in s:
            g = self.g(ch)
            if g and not ch.isspace():
                out.append('<use href="#%s" x="%d"/>' % (self.ref(g), cx))
            cx += self.adv(ch) + track * self.upm
        return '<g fill="%s" transform="translate(%.1f %.1f) scale(%.5f)"%s>%s</g>' % (fill, x, y, sc, attrs, ''.join(out))

    def defs(self):
        out = []
        for g in self.used:
            pen = SVGPathPen(self.gs, ntos=lambda v: str(round(v)))
            self.gs[g].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            out.append('<path id="%s" d="%s"/>' % (self.ref(g), pen.getCommands()))
        return ''.join(out)

def faces():
    return (Face(ROOT + '/fonts/unbounded-600-800-latin.woff2', 'u', wght=800),
            Face(ROOT + '/fonts/anonymous-pro-400-latin.woff2', 'a'),
            Face(ROOT + '/fonts/anonymous-pro-700-latin.woff2', 'b'))

def typed(mono, text, x, y, size, fill, start, per, cid, caret_fill, keep_caret):
    """a line that types itself in: a clip rect grows one character at a time, a caret rides its edge"""
    w, n = mono.width(text, size), len(text)
    dur = n * per
    cw = mono.adv('m') * size / mono.upm
    clip = ('<clipPath id="%s"><rect class="grow" x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
            'style="animation:grow %.2fs steps(%d,end) %.2fs both"/></clipPath>') % (cid, x, y - size, w + 2, size * 1.5, dur, n, start)
    caret = ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
             'style="animation:on .01s %.2fs both,slide %.2fs steps(%d,end) %.2fs both,%s;--w:%.1fpx"/>') % (
        x, y - size * .82, max(2, cw * .18), size, caret_fill, start, dur, n, start,
        'blink 1s steps(1) %.2fs infinite' % (start + dur) if keep_caret else 'gone .01s %.2fs forwards' % (start + dur + .4), w)
    return clip, '<g clip-path="url(#%s)">%s</g>%s' % (cid, mono.run(text, x, y, size, fill), caret)

CSS = '''
.grow{transform-box:fill-box;transform-origin:left center}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes slide{from{transform:translateX(0)}to{transform:translateX(var(--w))}}
@keyframes blink{50%{opacity:0}}
@keyframes gone{to{opacity:0}}
@keyframes on{from{opacity:0}to{opacity:1}}
@keyframes rise{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes drift{to{transform:translateY(var(--h))}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse{0%{transform:scale(1);opacity:.55}100%{transform:scale(3.2);opacity:0}}
.rule{transform-box:fill-box;transform-origin:left center;animation:draw 1.4s cubic-bezier(.65,0,.35,1) .2s both}
.l{animation:rise .9s cubic-bezier(.16,1,.3,1) both}
.f{animation:fade .8s ease both}
.guide{transform-box:fill-box;transform-origin:left center;animation:draw 1.1s cubic-bezier(.65,0,.35,1) both}
.ring{transform-box:view-box;animation:spin 48s linear infinite}
.ping{transform-box:fill-box;transform-origin:center;animation:pulse 2s cubic-bezier(.2,.6,.3,1) infinite}
@keyframes trace{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}
@keyframes orbit{from{stroke-dashoffset:0}to{stroke-dashoffset:-1000}}
@keyframes hit{0%{transform:scale(1);opacity:.7}14%,100%{transform:scale(3.6);opacity:0}}
@keyframes drop{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes sweep{0%{opacity:0;transform:translateX(0)}8%,92%{opacity:1}100%{opacity:0;transform:translateX(var(--w))}}
.track{stroke-dasharray:1000;animation:trace 2.2s cubic-bezier(.65,0,.35,1) .2s both}
.hit{opacity:0;transform-box:fill-box;transform-origin:center}
.vguide{transform-box:fill-box;transform-origin:center top;animation:drop 1s cubic-bezier(.65,0,.35,1) both}
@media (prefers-reduced-motion:reduce){*{animation-duration:0s!important;animation-delay:0s!important;animation-iteration-count:1!important}}
'''

def topbar(t, A, left, right):
    """live dot and a label on the left, a note on the right, then the violet rule drawing in"""
    return ['<circle cx="66" cy="44" r="4" fill="%s"/><circle class="ping" cx="66" cy="44" r="4" fill="%s"/>' % (t['violet'], t['violet']),
            A.run(left, 82, 49, 15, t['muted']),
            A.run(right, 1140 - A.width(right, 15), 49, 15, t['muted']),
            '<rect x="60" y="70" width="1080" height="1" fill="%s"/>' % t['line'],
            '<rect class="rule" x="60" y="69.5" width="1080" height="2" fill="%s"/>' % t['violet']]

def on_line(t, segs, x, y, size, face):
    """mono text sitting on a hairline, the line erased behind it; segs = ((text, fill), ...)"""
    w = sum(face.width(s, size) for s, _ in segs)
    out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (x - 10, y - size * .9, w + 20, size * 1.3, t['bg'])]
    for s, fill in segs:
        out.append(face.run(s, x, y, size, fill)); x += face.width(s, size)
    return ''.join(out)

def banner(theme):
    t = THEMES[theme]
    U, A, B = faces()
    W, H = 1200, 420
    parts, defs = [], []

    # hex dump drifting upward, the portfolio's background texture
    rnd = random.Random(7)
    words = ['7c00', 'nmap -sS -Pn', '── red ──', '── blue ──', 'mov ax, 0x13', '0x41414141', 'llm.jailbreak()', 'int 0x80']
    rows = []
    for _ in range(14):
        cells = []
        while sum(len(c) + 1 for c in cells) < 150:
            cells.append(rnd.choice(words) if rnd.random() < .06 else '%02x' % rnd.randrange(256))
        rows.append(' '.join(cells))
    lh = 19
    hexg = ''.join(A.run(r, 24, 30 + i * lh, 12, t['hex']) for i, r in enumerate(rows + rows))
    defs.append('<radialGradient id="hm" cx=".72" cy=".2" r=".85"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset=".75" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                '<mask id="hexmask"><rect width="%d" height="%d" fill="url(#hm)"/></mask>' % (W, H))
    parts.append('<g mask="url(#hexmask)" opacity="%s"><g style="animation:drift 70s linear infinite;--h:-%dpx">%s</g></g>'
                 % ('.10' if theme == 'light' else '.09', 14 * lh, hexg))

    # top bar: availability with a live dot, place on the right, then the violet rule drawing in
    parts += topbar(t, A, 'open to a 6-month final-year internship · jan 2027', 'paris, fr · 48.86°N 2.35°E')

    # wordmark with type-design guides, like the portfolio's hero
    size, x0, base, track = 150, 54, 262, -.02
    sc = size / U.upm
    xs, cx = [], x0
    for ch in 'shaïma':
        xs.append(cx); cx += (U.adv(ch) + track * U.upm) * sc
    wend = cx
    for name, y, d in (('cap', base - U.cap * sc, 1.5), ('x-height', base - U.xh * sc, 1.62), ('baseline', base, 1.74)):
        parts.append('<rect class="guide" x="40" y="%.1f" width="%.1f" height="1" fill="%s" opacity=".55" style="animation-delay:%.2fs"/>' % (y, wend - 40 + 14, t['muted'], d))
        parts.append('<g class="f" style="animation-delay:%.2fs">%s</g>' % (d + .5, A.run(name, wend + 22, y + 4, 11, t['muted'])))
    for i, ch in enumerate('shaïma'):
        parts.append('<g class="l" style="animation-delay:%.2fs">%s</g>' % (.25 + i * .07, U.run(ch, xs[i], base, size, t['ink'])))
    # dashed selection box around the ï, with handles and its code point
    bx0, by0, bx1, by1 = U.bounds('ï')
    i = 'shaïma'.index('ï')
    rx, ry, rw, rh = xs[i] + bx0 * sc - 8, base - by1 * sc - 8, (bx1 - bx0) * sc + 16, (by1 - by0) * sc + 16
    box = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="%s" stroke-width="1.3" stroke-dasharray="5 4"/>' % (rx, ry, rw, rh, t['violet'])]
    for hx, hy in ((rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)):
        box.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="%s" stroke="%s" stroke-width="1.3"/>' % (hx - 3.5, hy - 3.5, t['bg'], t['violet']))
    box.append(A.run('U+00EF', rx, ry - 9, 11, t['violet']))
    parts.append('<g class="f" style="animation-delay:1.25s">%s</g>' % ''.join(box))

    # the role types itself in under the name
    prompt = '$'
    parts.append('<g class="f" style="animation-delay:1.9s">%s</g>' % B.run(prompt, 60, 330, 20, t['violet']))
    role = 'application security engineer · ai security · llm red teaming'
    clip, line = typed(A, role, 84, 330, 20, t['ink'], 2.1, .034, 'tp', t['violet'], True)
    defs.append(clip); parts.append(line)
    facts = 'ece paris · meng cybersecurity · ai for security, and security for ai'
    parts.append('<g class="f" style="animation-delay:4.4s">%s</g>' % A.run(facts, 84, 362, 14, t['muted']))

    # rotating roundel: red team / blue team around a sober ï
    cxr, cyr, r = 1022, 205, 96
    ring_text = 'red team · blue team · ai security · llm red teaming · '
    n = len(ring_text)
    glyphs = []
    for k, ch in enumerate(ring_text):
        if ch == ' ':
            continue
        ang = k * 360 / n
        w = B.width(ch, 13)
        glyphs.append('<g transform="rotate(%.2f %d %d)">%s</g>' % (ang, cxr, cyr, B.run(ch, cxr - w / 2, cyr - r + 26, 13, t['ink'])))
    parts.append('<g class="f" style="animation-delay:.9s">'
                 '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="12"/>' % (cxr, cyr, r, t['violet']) +
                 '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="1"/>' % (cxr, cyr, r - 40, t['line']) +
                 '<g class="ring" style="transform-origin:%dpx %dpx">%s</g>' % (cxr, cyr, ''.join(glyphs)) + '</g>')
    ix0, iy0, ix1, iy1 = U.bounds('ï')
    isz = 64
    isc = isz / U.upm
    parts.append('<g class="f" style="animation-delay:1.1s">%s</g>' % U.run('ï', cxr - (ix0 + ix1) / 2 * isc, cyr + (iy0 + iy1) / 2 * isc, isz, t['ink']))

    # footer of the card
    parts.append('<rect x="60" y="388" width="1080" height="1" fill="%s"/>' % t['line'])
    parts.append('<g class="f" style="animation-delay:4.8s">%s%s</g>' % (
        A.run('shaima-drh.vercel.app', 60, 408, 13, t['violet']),
        A.run('github.com/shm0m', 1140 - A.width('github.com/shm0m', 13), 408, 13, t['muted'])))

    return svg(W, H, t, defs + [U.defs(), A.defs(), B.defs()], parts, 'Shaïma Derouich, application security engineer')

def footer(theme):
    t = THEMES[theme]
    U, A, B = faces()
    W, H = 1200, 168
    defs, parts = [], []
    parts.append(B.run('$', 60, 62, 18, t['violet']))
    c1, l1 = typed(A, 'ping shaima.derouich@proton.me', 82, 62, 18, t['ink'], .5, .045, 'p1', t['violet'], False)
    reply = '64 bytes from shaïma: icmp_seq=1 ttl=64 time=0.42 ms'
    parts += [l1, '<g class="f" style="animation-delay:2.1s">%s</g>' % A.run(reply, 82, 94, 16, t['muted'])]
    c2, l2 = typed(A, 'always down to talk deeptech.', 82, 128, 18, t['ink'], 2.7, .05, 'p2', t['violet'], True)
    parts.append(l2)
    defs += [c1, c2]
    return svg(W, H, t, defs + [U.defs(), A.defs(), B.defs()], parts, 'ping shaima.derouich@proton.me: always down to talk deeptech')

def method(theme):
    t = THEMES[theme]
    U, A, B = faces()
    W, H = 1200, 388
    parts = topbar(t, A, 'the method', 'find -> prove -> teach -> repeat')

    # the hunt never stops: a track loops around the three steps and a comet circles it forever
    x0, y0, x1, y1, r, dur, start = 40, 112, 1160, 344, 22, 10, 2.2
    d = ('M%d %dH%dA%d %d 0 0 1 %d %dV%dA%d %d 0 0 1 %d %dH%dA%d %d 0 0 1 %d %dV%dA%d %d 0 0 1 %d %dZ'
         % (x0 + r, y0, x1 - r, r, r, x1, y0 + r, y1 - r, r, r, x1 - r, y1, x0 + r, r, r, x0, y1 - r, y0 + r, r, r, x0 + r, y0))
    L = 2 * (x1 - x0 - 2 * r) + 2 * (y1 - y0 - 2 * r) + 2 * math.pi * r
    parts.append('<path class="track" d="%s" pathLength="1000" fill="none" stroke="%s"/>' % (d, t['line']))
    # a faint tail, and its bright head kept 70 units in front by starting earlier (var() in keyframes won't interpolate)
    for dash, ahead, op in (('90 910', 0, .3), ('20 980', 70, 1)):
        parts.append('<path d="%s" pathLength="1000" fill="none" stroke="%s" stroke-opacity="%s" stroke-width="2.5" stroke-linecap="round" '
                     'stroke-dasharray="%s" style="animation:orbit %ds linear %.2fs infinite both,fade .6s ease %.1fs both"/>'
                     % (d, t['violet'], op, dash, dur, start - ahead / 1000 * dur, start))

    cols = [84 + i * 360 for i in range(3)]
    steps = (('find', 'the flaw nobody modeled.', 'code, configs, prompts, weights.'),
             ('prove', "exploit it, or it isn't real.", 'no finding without a working proof.'),
             ('teach', 'hand the hunt to machines.', 'agents that never stop looking.'))
    for i, (x, (verb, l1, l2)) in enumerate(zip(cols, steps)):
        s = (x - x0 - r) / L * 1000                       # where this node sits on the track
        hit = start + (s - 90) % 1000 / 1000 * dur        # when the comet's head first reaches it
        node = ('<circle cx="%d" cy="%d" r="6" fill="%s" stroke="%s" stroke-width="1.5"/><circle cx="%d" cy="%d" r="2.5" fill="%s"/>'
                '<circle class="hit" cx="%d" cy="%d" r="6" fill="%s" style="animation:hit %ds cubic-bezier(.2,.6,.3,1) %.2fs infinite"/>'
                % (x, y0, t['bg'], t['violet'], x, y0, t['violet'], x, y0, t['violet'], dur, hit))
        parts.append('<g class="f" style="animation-delay:%.2fs">%s%s</g>' % (.5 + i * .3, on_line(t, (('0%d' % (i + 1), t['violet']),), x + 18, y0 + 5, 14, B), node))
        w = U.width(verb, 72, -.02)
        parts.append('<g class="l" style="animation-delay:%.2fs">%s%s</g>' % (.3 + i * .15, U.run(verb, x, 214, 72, t['ink'], -.02), U.run('.', x + w, 214, 72, t['violet'])))
        parts.append('<g class="f" style="animation-delay:%.2fs">%s%s</g>' % (1 + i * .2, A.run(l1, x, 260, 16, t['ink']), A.run(l2, x, 286, 16, t['muted'])))
        assert max(w + U.width('.', 72), A.width(l1, 16), A.width(l2, 16)) < 330, verb

    segs = (('while true; do ', t['muted']), ('hunt', t['violet']), ('; done', t['muted']))
    w = sum(A.width(s, 15) for s, _ in segs)
    parts.append('<g class="f" style="animation-delay:2s">%s</g>' % on_line(t, segs, (W - w) / 2, y1 + 5, 15, A))
    return svg(W, H, t, [U.defs(), A.defs(), B.defs()], parts, 'the method: find the flaw, prove it by exploiting it, teach machines to hunt it, repeat')

def arsenal(theme):
    t = THEMES[theme]
    U, A, B = faces()
    rows = (('offense', ('Burp Suite', 'Metasploit', 'Nmap', 'Ghidra', 'Kali Linux', 'threat modeling')),
            ('defense', ('SIEM', 'Wireshark', 'forensics', 'Linux hardening', 'MITRE ATT&CK', 'Dependency-Track', 'SDLC')),
            ('ai / ml', ('PyTorch', 'TensorFlow', 'scikit-learn', 'LangChain', 'RAG', 'MCP')),
            ('infra', ('Docker', 'Kubernetes', 'OpenShift', 'Ansible', 'GitLab CI/CD')),
            ('code', ('Python', 'Rust', 'C', 'Bash', 'TypeScript', 'Node.js', 'React', 'SQL')))
    W, top, rh, cx0, scan = 1200, 96, 64, 300, 2.4
    H = top + len(rows) * rh + 26
    parts = topbar(t, A, 'arsenal', '%d tools · %d domains' % (sum(len(r[1]) for r in rows), len(rows)))
    for i, (label, tools) in enumerate(rows):
        cy = top + i * rh + rh / 2
        if i:
            parts.append('<rect class="guide" x="60" y="%d" width="1080" height="1" fill="%s" style="animation-delay:%.2fs"/>' % (top + i * rh, t['line'], .3 + i * .08))
        parts.append('<g class="f" style="animation-delay:%.2fs">%s%s</g>' % (.3 + i * .08, A.run('0x%02x' % (i + 1), 60, cy + 5, 13, t['violet']),
                                                                             U.run(label, 112, cy + U.xh * 28 / U.upm / 2, 28, t['ink'])))
        x = cx0
        for tool in tools:  # each chip appears as the scan line passes over it
            w = A.width(tool, 15) + 28
            parts.append('<g class="f" style="animation-delay:%.2fs"><rect x="%.1f" y="%.1f" width="%.1f" height="34" rx="17" fill="none" stroke="%s" stroke-opacity=".5"/>%s</g>'
                         % (.5 + (x - cx0) / (1140 - cx0) * scan, x, cy - 17, w, t['muted'], A.run(tool, x + 14, cy + 5, 15, t['ink'])))
            x += w + 10
        assert x - 10 <= 1140, label
    parts.append('<rect x="%d" y="%d" width="2" height="%d" fill="%s" style="animation:sweep %.1fs cubic-bezier(.45,0,.55,1) .5s both;--w:%dpx"/>'
                 % (cx0 - 12, top + 8, len(rows) * rh - 16, t['violet'], scan, 1140 - cx0 + 12))
    alt = 'arsenal: ' + '; '.join('%s: %s' % (label, ', '.join(tools)) for label, tools in rows)
    return svg(W, H, t, [U.defs(), A.defs(), B.defs()], parts, alt.replace('&', '&amp;'))

def proof(theme):
    t = THEMES[theme]
    U, A, B = faces()
    W, H = 1200, 296
    parts = topbar(t, A, 'proof of work', 'root-me @klawd1 · tryhackme @kl4wd')
    cells = (('root-me', '2200', '+', 'points · 105 challenges'),
             ('tryhackme', 'top 4', '%', 'worldwide · 98 rooms · 23 badges'),
             ('certified', '04', '', 'aws · comptia cysa+ · thm · anssi'))
    size = min(76, min(320 / U.width(big + acc, 1, -.02) for _, big, acc, _ in cells))
    for i, (label, big, acc, cap) in enumerate(cells):
        x = 60 + i * 380
        if i:
            parts.append('<rect class="vguide" x="%d" y="104" width="1" height="160" fill="%s" style="animation-delay:%.2fs"/>' % (x - 30, t['line'], .4 + i * .1))
        parts.append('<g class="f" style="animation-delay:%.2fs">%s</g>' % (.3 + i * .2, A.run(label, x, 120, 14, t['muted'])))
        for k, ch in enumerate(big + acc):  # numerals rise one by one, the unit in violet
            parts.append('<g class="l" style="animation-delay:%.2fs">%s</g>' % (.4 + i * .2 + k * .06, U.run(ch, x, 212, size, t['violet'] if k >= len(big) else t['ink'])))
            x += U.width(ch, size, -.02)
        parts.append('<g class="f" style="animation-delay:%.2fs">%s</g>' % (1.2 + i * .2, A.run(cap, 60 + i * 380, 252, 15, t['muted'])))
    return svg(W, H, t, [U.defs(), A.defs(), B.defs()], parts,
               'proof of work: 2200+ points on Root-Me (105 challenges), top 4% worldwide on TryHackMe (98 rooms, 23 badges), 4 certifications (AWS, CompTIA CySA+, TryHackMe, ANSSI)')

def svg(W, H, t, defs, parts, title):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title><style>%s</style><defs><clipPath id="card"><rect width="%d" height="%d" rx="14"/></clipPath>%s</defs>'
            '<rect x=".5" y=".5" width="%d" height="%d" rx="14" fill="%s" stroke="%s"/>'
            '<g clip-path="url(#card)">%s</g></svg>') % (W, H, W, H, title, title, CSS, W, H, ''.join(defs), W - 1, H - 1, t['bg'], t['line'], ''.join(parts))

for theme in THEMES:
    for name, fn in (('banner', banner), ('footer', footer), ('method', method), ('arsenal', arsenal), ('proof', proof)):
        p = '%s/%s-%s.svg' % (OUT, name, theme)
        open(p, 'w', encoding='utf-8').write(fn(theme))
        print(p, os.path.getsize(p) // 1024, 'KB')
