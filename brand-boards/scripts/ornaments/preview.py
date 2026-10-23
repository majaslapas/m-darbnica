import os, sys, re, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B
from geom import fmt

ROOT = B.ROOT
P = B.PREVIEW
FONTS = ROOT + '/fonts'
LOGO_D = re.search(r' d="([^"]+)"', open(ROOT + '/logo/m_logo.svg').read()).group(1)
PHOTOS = {'round': ROOT + '/assets4/a_hero_col.jpg', 'keyhole': ROOT + '/assets4/e_player_col.jpg',
          'ogee': ROOT + '/assets5/c_sax_street_col.jpg'}


def paths(layers, color=None):
    out = []
    for L in layers:
        c = color or 'currentColor'
        if L['kind'] == 'stroke':
            out.append(f'<path d="{L["path"].d()}" fill="none" stroke="{c}" stroke-width="{fmt(L["sw"], 3)}" '
                       f'stroke-linecap="{L.get("cap", "round")}" stroke-linejoin="{L.get("join", "round")}"/>')
        else:
            out.append(f'<path d="{L["path"].d()}" fill="{c}"/>')
    return ''.join(out)


def svg(vb, layers, w=None, h=None, extra='', cls='', style=''):
    vw, vh = vb[2], vb[3]
    if w is None and h is None:
        w, h = vw, vh
    elif w is None:
        w = h * vw / vh
    elif h is None:
        h = w * vh / vw
    return (f'<svg class="{cls}" style="{style}" viewBox="{B.vbstr(vb)}" width="{fmt(w, 1)}" height="{fmt(h, 1)}">'
            f'{extra}{paths(layers)}</svg>')


def logo(cx, cy, r):
    s = 2 * r / 100
    return f'<path d="{LOGO_D}" fill="currentColor" fill-rule="evenodd" transform="translate({cx - r} {cy - r}) scale({s})"/>'


def mirror(layers, sx, sy, W, H):
    return [dict(L, path=L['path'].affine([[sx, 0, W if sx < 0 else 0], [0, sy, H if sy < 0 else 0]])) for L in layers]


def frame_svg(cL, S, FWu, FHu, insets, width, inner=''):
    parts = []
    for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        m = [[sx, 0, FWu if sx < 0 else 0], [0, sy, FHu if sy < 0 else 0]]
        parts.append(paths([dict(L, path=L['path'].affine(m)) for L in cL]))
    for off, sw in insets:
        d = (f'M{S} {off}H{FWu - S}M{S} {FHu - off}H{FWu - S}'
             f'M{off} {S}V{FHu - S}M{FWu - off} {S}V{FHu - S}')
        parts.append(f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="butt"/>')
    h = width * FHu / FWu
    return f'<svg viewBox="0 0 {FWu} {FHu}" width="{width}" height="{fmt(h, 1)}">{"".join(parts)}{inner}</svg>'


def page(theme):
    if theme == 'light':
        ink, paper, mute, onphoto = '#1F1D1A', '#EFE9DD', 'rgba(31,29,26,.55)', '#EFE9DD'
    else:
        ink, paper, mute, onphoto = '#F4E9D8', '#22382D', 'rgba(244,233,216,.6)', '#F4E9D8'
    A = P['arches']
    # --- 01 arches -----------------------------------------------------
    cells = []
    for key in ('round', 'keyhole', 'ogee'):
        a = A[key]
        solid = svg((0, 0, 200, 300), [dict(kind='fill', sw=0, path=a['px'])], 132)
        outline = svg((0, 0, 200, 300), a['outline'], 132)
        photo = (f'<svg viewBox="0 0 200 300" width="132" height="198">'
                 f'<image href="file://{PHOTOS[key]}" x="0" y="0" width="200" height="300" preserveAspectRatio="xMidYMid slice" '
                 f'clip-path="url(#md-arch-{key})"/>{paths(a["outline"], onphoto)}</svg>')
        cells.append(f'<figure class="arch"><div class="trip">{solid}{outline}{photo}</div>'
                     f'<figcaption><b>{a["label"]}</b><span>arch-{key}-clip.svg · arch-{key}-outline.svg</span></figcaption></figure>')
    sec1 = f'<section class="s1"><h2><i>01</i>Arch frames <em>clip-path (objectBoundingBox) · outline · in use</em></h2><div class="row">{"".join(cells)}</div></section>'

    # --- 02 whiplash ---------------------------------------------------
    vb, L = P['h_stroke']
    vbt, Lt = P['h_fill']
    vbd, Ld = P['div']
    vbdt, Ldt = P['divt']
    vbv, Lv = P['v_stroke']
    vbvt, Lvt = P['v_fill']
    sec2 = f'''<section class="s2"><h2><i>02</i>Whiplash <em>divider · underline · horizontal &amp; vertical</em></h2>
    <div class="wgrid">
      <div class="wcol">
        <figure>{svg(vb, L, 700)}<figcaption><b>Horizontal</b><span>whiplash-h.svg</span></figcaption></figure>
        <figure>{svg(vbt, Lt, 700)}<figcaption><b>Horizontal, tapered</b><span>whiplash-h-tapered.svg</span></figcaption></figure>
        <figure>{svg(vbd, Ld, 1060)}<figcaption><b>Centred divider</b><span>whiplash-divider.svg</span></figcaption></figure>
        <figure>{svg(vbdt, Ldt, 1060)}<figcaption><b>Centred divider, tapered</b><span>whiplash-divider-tapered.svg</span></figcaption></figure>
      </div>
      <div class="vpair">
        <figure>{svg(vbv, Lv, h=400)}</figure>
        <figure>{svg(vbvt, Lvt, h=400)}</figure>
        <figcaption><b>Vertical</b><span>whiplash-v.svg · -tapered</span></figcaption>
      </div>
    </div></section>'''

    # --- 03 secession / 04 stem ---------------------------------------
    tvb, tL = P['tile']
    tile_big = svg(tvb, tL, h=150, cls='tile')
    strip = (f'<div class="strip" style="height:60px;-webkit-mask:url(file://{B.OUT}/secession-border-tile.svg) repeat-x left top / auto 60px;'
             f'mask:url(file://{B.OUT}/secession-border-tile.svg) repeat-x left top / auto 60px;background:{ink}"></div>')
    strip_small = (f'<div class="strip" style="height:30px;-webkit-mask:url(file://{B.OUT}/secession-border-tile.svg) repeat-x left top / auto 30px;'
                   f'mask:url(file://{B.OUT}/secession-border-tile.svg) repeat-x left top / auto 30px;background:{ink}"></div>')
    vstrip = (f'<div class="vstrip" style="width:44px;height:360px;-webkit-mask:url(file://{B.OUT}/secession-border-tile-v.svg) repeat-y left top / 44px auto;'
              f'mask:url(file://{B.OUT}/secession-border-tile-v.svg) repeat-y left top / 44px auto;background:{ink}"></div>')
    pvb, pL = P['pil']
    svb, sL = P['sun']
    sec3 = f'''<section class="s3"><h2><i>03</i>Secession border <em>repeat tile · Moser bars &amp; Hoffmann squares</em></h2>
      <div class="secgrid">
        <div class="seccol">
          <figure>{strip}<figcaption><b>Border, repeat-x</b><span>secession-border-tile.svg (48 × 60, seamless)</span></figcaption></figure>
          <figure>{strip_small}<figcaption><b>Same tile at half size</b><span>background-size: auto 30px</span></figcaption></figure>
          <figure class="tilefig">{tile_big}<figcaption><b>One tile</b><span>dashed = repeat boundary</span></figcaption></figure>
        </div>
        <figure class="vs">{vstrip}<figcaption><b>repeat-y</b><span>-tile-v.svg</span></figcaption></figure>
        <figure class="pil">{svg(pvb, pL, h=360)}<figcaption><b>Pilaster</b><span>secession-pilaster.svg</span></figcaption></figure>
      </div></section>
      <section class="s4" style="width:190px"><h2><i>04</i>Stem &amp; bloom</h2>
        <figure class="sun">{svg(svb, sL, h=430)}<figcaption><b>Sunflower</b><span>stem-sunflower.svg</span></figcaption></figure>
      </section>'''

    # --- 05 corners ------------------------------------------------------
    cvb, cL = P['corner']
    c2vb, c2L = P['corner2']
    S = cvb[2]
    y0 = B.O.CO['y0']
    g = B.O.CO['y0'] + B.O.CO['gap']
    FWu, FHu = 700, 460
    hvb, hL = P['halo']
    # halo + logo centred inside the looped frame (halo box 300 units)
    hs = 300 / 400
    inner = (f'<g transform="translate({FWu / 2 - 150} {FHu / 2 - 150}) scale({hs})">{paths(hL)}{logo(200, 200, 100)}</g>')
    frame1 = frame_svg(cL, S, FWu, FHu, [(y0, 1.5), (g, 0.75)], 520, inner)
    S2 = c2vb[2]
    frame2 = frame_svg(c2L, S2, 380, 440, [(22, 1.5), (28, 0.75)], 300)
    sec5 = f'''<section class="s5"><h2><i>06</i>Corner flourishes <em>one corner, mirrored ×4</em></h2>
      <div class="cgrid">
        <figure>{svg(cvb, cL, 240, cls='dash')}<figcaption><b>Looped rule</b><span>corner-loop.svg (top-left)</span></figcaption></figure>
        <figure>{frame1}
          <figcaption><b>Mirrored into a frame</b><span>scale(-1,1) · scale(1,-1) · scale(-1,-1); rules continue as 1.5 / 0.75 lines</span></figcaption></figure>
        <figure>{svg(c2vb, c2L, 180, cls='dash')}<figcaption><b>Secession alternative</b><span>corner-secession.svg</span></figcaption></figure>
        <figure>{frame2}<figcaption><b>Mirrored</b><span>crossing rules + checker</span></figcaption></figure>
      </div></section>'''

    sec6 = f'''<section class="s6"><h2><i>05</i>Halo / sunburst <em>behind the circular logo</em></h2>
      <div class="hgrid">
        <figure>{svg(hvb, hL, 340, extra=logo(200, 200, 100))}<figcaption><b>With logo</b><span>halo-sunburst.svg · 24 bundles × 3 rays · logo Ø = ½ box</span></figcaption></figure>
      </div></section>'''

    css = f'''
@font-face{{font-family:IS;src:url(file://{FONTS}/Instrument_Sans.latin.woff2) format('woff2');font-weight:400 700}}
@font-face{{font-family:ISe;src:url(file://{FONTS}/Instrument_Serif.latin.woff2) format('woff2')}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:{paper};color:{ink}}}\n:root{{--h:2330px}}
body{{width:1600px;height:var(--h);padding:56px 64px;font-family:IS,sans-serif;font-size:12px;position:relative;overflow:hidden}}
header{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1.5px solid {ink};padding-bottom:14px;margin-bottom:34px}}
header h1{{font-family:ISe,serif;font-weight:400;font-size:54px;letter-spacing:-.01em;line-height:1}}
header h1 small{{font-family:IS;font-size:13px;letter-spacing:.22em;text-transform:uppercase;display:block;margin-bottom:12px}}
header p{{font-size:12px;letter-spacing:.06em;line-height:1.6;text-align:right;color:{mute}}}
h2{{font-size:12px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;display:flex;align-items:baseline;gap:12px;margin-bottom:20px}}
h2 i{{font-style:normal;font-family:ISe;font-size:26px;letter-spacing:0;font-weight:400}}
h2 em{{font-style:normal;font-weight:400;letter-spacing:.06em;text-transform:none;color:{mute}}}
figure{{display:flex;flex-direction:column;gap:10px}}
figcaption{{display:flex;flex-direction:column;gap:3px;font-size:11.5px;letter-spacing:.02em}}
figcaption b{{font-weight:600}}
figcaption span{{color:{mute}}}
section{{margin-bottom:50px}}
.s1 .row{{display:flex;justify-content:space-between}}
.trip{{display:flex;gap:14px;align-items:flex-end}}
.wgrid{{display:flex;justify-content:space-between;align-items:flex-start}}
.wcol{{display:flex;flex-direction:column;gap:28px}}
.vpair{{display:grid;grid-template-columns:auto auto;gap:10px 56px;margin-right:40px}}
.vpair figcaption{{grid-column:1/3}}
.mid{{display:flex;justify-content:space-between;align-items:flex-start}}
.secgrid{{display:flex;gap:40px;align-items:flex-start}}
.seccol{{display:flex;flex-direction:column;gap:26px;width:672px}}
.tile{{outline:1px dashed {mute};outline-offset:0}}
.dash{{outline:1px dashed {mute}}}
.cgrid{{display:flex;justify-content:space-between;align-items:flex-start}}
.frame{{position:relative}}
.hgrid{{display:flex;gap:60px;align-items:center}}
.bottom{{display:flex;gap:90px;align-items:flex-start}}
footer{{position:absolute;left:64px;right:64px;bottom:40px;display:flex;justify-content:space-between;border-top:.75px solid {ink};padding-top:10px;color:{mute};letter-spacing:.05em}}
'''
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs>{P['clip_defs']}</defs></svg>
<header><h1><small>M/darbnīca · new retro direction</small>Jugendstil ornament kit</h1>
<p>Rīga Art Nouveau &amp; Vienna Secession, redrawn as clean single-colour line work<br>
every file: currentColor · paths of M/L/C only · main line 1.5 · hairline 0.75</p></header>
{sec1}
{sec2}
<div class="mid">{sec3}{sec6}</div>
{sec5}
<footer><span>assets6/ornaments/ — {len(B.files)} SVG + ornaments.json</span><span>{'ink #1F1D1A on #EFE9DD' if theme == 'light' else 'cream #F4E9D8 on #22382D'}</span></footer>
</body></html>'''
    return html


for theme, name in [('light', 'preview_ink-on-paper'), ('dark', 'preview_cream-on-green')]:
    p = f'{B.WORK}/{name}.html'
    open(p, 'w').write(page(theme))
    print(p)
