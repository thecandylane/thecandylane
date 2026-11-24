# Builds thecandylane/header.svg: a phosphor terminal that types the boot log, Temple8 embedded as a data URI.
# Usage: python3 make_header.py ../jack-site/public/fonts/temple8.woff header.svg  (edit LINES, e.g. the ref count, then rerun)
import base64, sys, html
font = base64.b64encode(open(sys.argv[1], 'rb').read()).decode()
LINES = [  # (kind, text)
    ('cmd', 'whoami'),
    ('out', 'jack schliewe · ai and cyber engineer @ farmmind · baton rouge, la'),
    ('cmd', 'cat motto'),
    ('out', 'I build custom, secure hardware and software.'),
    ('cmd', 'ref search "who already built this?"'),
    ('out', '7,600+ curated refs · 358 topics · ref.lookit.space/mcp'),
]
FS, CW, LH, X0, Y0 = 13, 13, 24, 28, 64   # font size, char width (8x8 font: advance = size), line height, origin
W = X0 * 2 + CW * max(len(t) + (2 if k == 'cmd' else 0) for k, t in LINES)
H = Y0 + LH * len(LINES) + 28
rows, t = [], 0.4
steps = lambda k, w: ';'.join(f'{round(w * j / k)} 0' for j in range(k + 1))
for i, (kind, text) in enumerate(LINES):
    s = ('$ ' if kind == 'cmd' else '') + text
    n = len(s); y = Y0 + i * LH
    dur = n * 0.035 if kind == 'cmd' else 0.05
    cls = 'c' if kind == 'cmd' else 'o'
    body = f'<tspan class="p">$ </tspan>{html.escape(text)}' if kind == 'cmd' else html.escape(text)
    rows.append(f'<text class="{cls}" x="{X0}" y="{y}">{body}</text>'
                f'<rect class="cover" x="{X0 - 2}" y="{y - FS - 5}" width="{n * CW + 10}" height="{FS + 12}">'
                f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" fill="freeze" begin="{t:.2f}s" dur="{dur:.2f}s" '
                f'values="{steps(n if kind == 'cmd' else 1, n * CW + 6)}"/></rect>')
    t += dur + (0.25 if kind == 'cmd' else 0.45)
cy = Y0 + len(LINES) * LH
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="$ whoami: jack schliewe, ai and cyber engineer at farmmind, baton rouge. I build custom, secure hardware and software. ref-radar: 7,600+ curated refs at ref.lookit.space">
<style>
@font-face {{ font-family: T8; src: url(data:font/woff;base64,{font}) format('woff'); }}
text {{ font-family: T8, ui-monospace, monospace; font-size: {FS}px; fill: #c8f5d3; filter: url(#glow); }}
.c, .p {{ fill: #5dff8a; }} .p {{ fill: #5d8f6a; }}
.cover {{ fill: #030d07; }}
.cur {{ fill: #5dff8a; }}
@media (prefers-reduced-motion: reduce) {{ .cover {{ display: none }}  }}
</style>
<defs>
<filter id="glow" x="-5%" y="-50%" width="110%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".22"/></pattern>
</defs>
<rect width="{W}" height="{H}" rx="10" fill="#030d07"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="#174224"/>
<text x="{X0}" y="30" style="fill:#5d8f6a;filter:none">thecandylane@schliewesystems: ~</text>
<circle cx="{W - 64}" cy="25" r="5" fill="#174224"/><circle cx="{W - 46}" cy="25" r="5" fill="#174224"/><circle cx="{W - 28}" cy="25" r="5" fill="#5dff8a" opacity=".7"/>
{"".join(rows)}
<rect class="cur" x="{X0}" y="{cy - FS}" width="{CW}" height="{FS + 2}" opacity="0"><animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.06s" begin="{t:.2f}s" repeatCount="indefinite"/></rect>
<rect width="{W}" height="{H}" rx="10" fill="url(#scan)" pointer-events="none"/>
</svg>'''
open(sys.argv[2], 'w').write(svg)
print(W, H, len(svg), 'bytes')
