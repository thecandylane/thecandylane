#!/usr/bin/env python3
# Builds card.svg: stack, contributions, languages, merged pull requests and tokens, in schliewesystems.com's phosphor style.
# Data: GitHub's GraphQL API through the gh CLI, tokenhub's stats on this Mac, and the Mac mini's Claude Code stats cache over ssh.
# Usage: python3 card.py   (update.sh runs it every 6 hours and pushes the result)
import base64, datetime as dt, html, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGIN = 'thecandylane'
FONT = os.environ.get('TEMPLE8', os.path.expanduser('~/Dev/code/jack-site/public/fonts/temple8.woff'))
TOKENHUB = os.environ.get('TOKENHUB_DIR', os.path.expanduser('~/Dev/tokenhub'))
MINI = os.environ.get('MINI_SSH', 'candylane@candylane-macmini')
TOKEN_GOAL = 100e9
BG, FG, MUTED, ACCENT, FRAME = '#030d07', '#c8f5d3', '#5d8f6a', '#5dff8a', '#174224'


def gql(query, **v):
    args = ['gh', 'api', 'graphql', '-f', f'query={query}']
    for k, x in v.items():
        args += ['-F', f'{k}={x}']
    return json.loads(subprocess.run(args, check=True, capture_output=True, text=True).stdout)['data']


# --- data -------------------------------------------------------------------------------------------------------

def github():
    years = gql('query($l:String!){user(login:$l){contributionsCollection{contributionYears}}}', l=LOGIN)['user']['contributionsCollection']['contributionYears']
    days, langs = {}, {}
    for y in years:
        c = gql('''query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t){
              contributionCalendar{weeks{contributionDays{date contributionCount}}}
              commitContributionsByRepository(maxRepositories:100){contributions{totalCount}
                repository{languages(first:10,orderBy:{field:SIZE,direction:DESC}){totalSize edges{size node{name}}}}}}}}''',
                l=LOGIN, f=f'{y}-01-01T00:00:00Z', t=f'{y}-12-31T23:59:59Z')['user']['contributionsCollection']
        for w in c['contributionCalendar']['weeks']:
            for d in w['contributionDays']:
                days[dt.date.fromisoformat(d['date'])] = d['contributionCount']
        for r in c['commitContributionsByRepository']:  # a repo's commits split across its languages by bytes
            n, l = r['contributions']['totalCount'], r['repository']['languages']
            for e in l['edges'] if l['totalSize'] else []:
                langs[e['node']['name']] = langs.get(e['node']['name'], 0) + n * e['size'] / l['totalSize']
    count = lambda q: gql('query($q:String!){search(query:$q,type:ISSUE,first:0){issueCount}}', q=q)['search']['issueCount']
    merged, public = count(f'is:pr is:merged author:{LOGIN}'), count(f'is:pr is:merged author:{LOGIN} is:public')
    nodes = gql('query($q:String!){search(query:$q,type:ISSUE,first:100){nodes{...on PullRequest{repository{nameWithOwner stargazerCount}}}}}',
                q=f'is:pr is:merged author:{LOGIN} is:public')['search']['nodes']
    repos = {}
    for n in nodes:
        r = n['repository']; repos.setdefault(r['nameWithOwner'], [r['stargazerCount'], 0])[1] += 1
    return days, langs, merged, public, sorted(repos.items(), key=lambda kv: -kv[1][1])


def streaks(days, today):
    best = run = 0
    for d in sorted(days):
        run = run + 1 if days[d] else 0
        best = max(best, run)
    cur, d = 0, today if days.get(today) else today - dt.timedelta(days=1)  # today still counts until it ends
    while days.get(d):
        cur, d = cur + 1, d - dt.timedelta(days=1)
    return cur, best


def tokens():
    """tokenhub's all-time count on this Mac plus the mini's Claude Code stats; a machine that can't be read keeps its last value."""
    path = os.path.join(HERE, 'tokens.json')
    last = json.load(open(path)) if os.path.exists(path) else {}
    out = dict(last)
    try:
        sys.path.insert(0, TOKENHUB); import stats
        r = stats.compute(period='all')
        out['macbook'] = r['tokens_cc'] or r['tokens']
    except Exception as e:
        print('tokenhub not read:', e, file=sys.stderr)
    read = ('import json,os;d=json.load(open(os.path.expanduser("~/.claude/stats-cache.json")));'
            'print(sum(u.get(k,0) for u in d["modelUsage"].values() for k in ("inputTokens","outputTokens","cacheReadInputTokens","cacheCreationInputTokens")))')
    try:
        p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', MINI, f"python3 -c '{read}'"],
                           capture_output=True, text=True, timeout=30)
        out['mini'] = int(p.stdout.strip())
    except Exception as e:
        print('mini not read:', e, file=sys.stderr)
    json.dump(out, open(path, 'w'), indent=1)
    return out


# --- drawing ----------------------------------------------------------------------------------------------------

W = 850
esc = html.escape


def text(x, y, s, size=12, fill=MUTED, anchor='start', t8=False, glow=False):
    cls = ' class="t8"' if t8 else ''
    f = ' filter="url(#glow)"' if glow else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{cls}{f}>{esc(str(s))}</text>'


def label(x, y, head, tail=''):
    return f'<text x="{x}" y="{y}" font-size="12" fill="{MUTED}"><tspan fill="{FG}">{esc(head)}</tspan>{" · " + esc(tail) if tail else ""}</text>'


def meter(x, y, w, frac, h=10):
    fill = max(0.0, min(1.0, frac)) * w
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{FRAME}"/>'
            f'<rect x="{x}" y="{y}" width="{fill:.1f}" height="{h}" rx="2" fill="{ACCENT}" filter="url(#glow)"/>')


def bar(x, base, w, h):
    """A bar anchored to the baseline with only its top corners rounded."""
    if h <= 0:
        return f'<rect x="{x:.1f}" y="{base - 1}" width="{w:.1f}" height="1" fill="{FRAME}"/>'
    r = min(2, h, w / 2)
    return (f'<path d="M{x:.1f},{base} V{base - h + r:.1f} Q{x:.1f},{base - h:.1f} {x + r:.1f},{base - h:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{base - h:.1f} {x + w:.1f},{base - h + r:.1f} V{base} Z" fill="{ACCENT}"/>')


def icons(y, size=26, gap=12):
    data = json.load(open(os.path.join(HERE, 'icons.json')))
    out, n = [], 0
    for i, row in enumerate(data['rows']):
        widths = [len(g) * (size + gap) - gap for g in row]
        total = sum(widths) + (len(row) - 1) * 28
        x, yy = (W - total) / 2, y + i * (size + 16)
        for gi, g in enumerate(row):
            for s in g:
                ic = data['icons'][s]
                out.append(f'<g transform="translate({x:.1f},{yy}) scale({size / 24})" fill="{ACCENT}" filter="url(#glow)">'
                           f'<title>{esc(ic["title"])}</title><path d="{ic["d"]}"/></g>')
                x += size + gap; n += 1
            if gi < len(row) - 1:
                out.append(f'<circle cx="{x - gap + 14:.1f}" cy="{yy + size / 2}" r="2" fill="{MUTED}"/>')
                x += 28 - gap
    return ''.join(out), n


def render(days, langs, merged, public, repos, tok, now):
    today = now.date()
    font = base64.b64encode(open(FONT, 'rb').read()).decode()
    last31 = [today - dt.timedelta(days=30 - i) for i in range(31)]
    counts = [days.get(d, 0) for d in last31]
    cur, best = streaks(days, today)
    total = sum(days.values())
    icon_svg, n_icons = icons(196)
    p = []
    hr = lambda y: p.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{FRAME}" stroke-dasharray="3 3"/>')

    # title bar and name
    p.append(text(24, 26, LOGIN, 13, FG, t8=True))
    p.append(text(W - 24, 26, '~/readme', 13, MUTED, 'end', t8=True))
    hr(42)
    p.append(text(24, 104, 'JACK SCHLIEWE', 52, FG, t8=True, glow=True))
    p.append(f'<rect x="{24 + 13 * 52 + 6}" y="62" width="30" height="46" fill="{ACCENT}" filter="url(#glow)">'
             '<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.06s" repeatCount="indefinite"/></rect>')
    p.append(text(24, 134, 'I build custom, secure hardware and software.', 13, MUTED))
    hr(152)

    # stack
    p.append(label(24, 178, 'STACK', f'{n_icons} tools'))
    p.append(icon_svg)
    hr(282)

    # contributions, last 31 days
    p.append(label(24, 308, 'CONTRIBUTIONS', f'{sum(counts):,} in the last 31 days'))
    cx, cw, base, ch = 24, 470, 440, 100
    bw = (cw - 30 * 3) / 31
    peak = max(counts) or 1
    for i, c in enumerate(counts):
        p.append(bar(cx + i * (bw + 3), base, bw, c / peak * ch))
    pi = counts.index(peak)
    p.append(text(cx + pi * (bw + 3) + bw / 2, base - ch - 8, f'{peak:,}', 11, FG, 'middle'))
    p.append(text(cx, base + 20, last31[0].strftime('%b %-d').lower(), 11))
    p.append(text(cx + cw, base + 20, 'today', 11, MUTED, 'end'))

    # totals
    tx = 540
    p.append(label(tx, 308, 'TOTALS', f'since {min(days):%Y}'))
    for i, (num, what) in enumerate([(f'{total:,}', 'contributions'), (str(cur), 'day streak, current'), (str(best), 'day streak, best')]):
        y = 350 + i * 36
        p.append(text(tx, y, num, 26, FG, t8=True, glow=True))
        p.append(text(tx + 150, y - 4, what, 12))
    p.append(meter(tx, 448, 220, cur / best if best else 0))
    p.append(text(W - 24, 457, f'{cur}/{best}', 13, FG, 'end', t8=True))
    hr(478)

    # languages, weighted by commits
    p.append(label(24, 504, 'LANGUAGES', 'by commits'))
    tot = sum(langs.values()) or 1
    for i, (name, v) in enumerate(sorted(langs.items(), key=lambda kv: -kv[1])[:6]):
        y = 532 + i * 24
        p.append(text(24, y, name.lower(), 12, FG))
        p.append(meter(130, y - 9, 200, v / tot))
        p.append(text(400, y, f'{v / tot:.1%}', 12, FG, 'end'))
    p.append(f'<line x1="425" y1="478" x2="425" y2="680" stroke="{FRAME}" stroke-dasharray="3 3"/>')

    # merged pull requests
    px = 448
    p.append(label(px, 504, 'PULL REQUESTS', 'merged'))
    p.append(text(px, 548, f'{merged:,}', 36, FG, t8=True, glow=True))
    p.append(text(px + 130, 530, 'merged pull requests', 12, FG))
    p.append(text(px + 130, 546, f'{merged - public:,} in private work repos, {public} public', 11))
    for i, (name, (stars, n)) in enumerate(repos[:5]):
        y = 578 + i * 19
        owner, _, rn = name.partition('/')
        p.append(f'<text x="{px}" y="{y}" font-size="11" fill="{MUTED}">{esc(owner)}/<tspan fill="{FG}">{esc(rn)}</tspan></text>')
        p.append(text(W - 64, y, f'{stars:,}★' if stars < 1000 else f'{stars / 1000:.1f}k★', 11, MUTED, 'end'))
        p.append(text(W - 24, y, n, 11, FG, 'end'))
    hr(680)

    # tokens
    mb, mini = tok.get('macbook', 0), tok.get('mini', 0)
    allt = mb + mini
    p.append(label(24, 706, 'TOKENS', f'measured by tokenhub · synced {now:%b %-d}'.lower()))
    p.append(text(24, 760, f'{allt:,}', 44, FG, t8=True, glow=True))
    p.append(text(24 + len(f'{allt:,}') * 44 + 16, 752, f'≈ {allt / 1e9:.1f} billion tokens', 13, FG))
    p.append(meter(24, 778, 640, allt / TOKEN_GOAL, 12))
    p.append(text(W - 24, 789, f'{allt / 1e9:.1f}B/{TOKEN_GOAL / 1e9:.0f}B', 13, FG, 'end', t8=True))
    p.append(text(24, 812, f'macbook since aug 2026 {mb / 1e9:.1f}B · mac mini since may 2026 {mini / 1e9:.1f}B · '
                           'an older laptop, used since oct 2025, isn\'t metered', 11))
    hr(832)

    # footer
    p.append(f'<rect x="24" y="851" width="6" height="6" fill="{ACCENT}"/>')
    p.append(text(38, 858, 'regenerated every 6h on my mac', 11))
    p.append(text(W - 24, 858, f'last sync {now:%Y-%m-%d %H:%M} utc', 11, MUTED, 'end'))

    H = 878
    summary = (f'Jack Schliewe (thecandylane). {n_icons} tools. {sum(counts):,} contributions in the last 31 days, {total:,} in all; '
               f'streak {cur} days, best {best}. {merged:,} merged pull requests. {allt / 1e9:.1f} billion tokens measured by tokenhub.')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(summary)}">
<title>{esc(summary)}</title>
<style>
@font-face {{ font-family: T8; src: url(data:font/woff;base64,{font}) format('woff'); }}
text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.t8 {{ font-family: T8, ui-monospace, monospace; }}
</style>
<defs>
<filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".2"/></pattern>
</defs>
<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{FRAME}"/>
{"".join(p)}
<rect width="{W}" height="{H}" rx="10" fill="url(#scan)" pointer-events="none"/>
</svg>'''


if __name__ == '__main__':
    now = dt.datetime.now(dt.timezone.utc)
    svg = render(*github(), tokens(), now)
    open(os.path.join(HERE, 'card.svg'), 'w').write(svg)
    print(f'card.svg written, {len(svg):,} bytes')
