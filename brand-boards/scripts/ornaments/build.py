"""Write the ornament kit: one SVG per ornament + ornaments.json + two preview pages."""
import os, sys, math, json, re, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ornaments as O
from geom import Path, fmt

ROOT = os.environ.get('MD_BOARDS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = ROOT + '/assets6/ornaments'
WORK = ROOT + '/work/ornaments'
os.makedirs(OUT, exist_ok=True)

ITEMS = {}      # name -> dict(viewBox=(x,y,w,h), layers=[...], ...)


def vbstr(vb):
    return ' '.join(fmt(v, 2) for v in vb)


def layer_json(L, prec=2):
    d = dict(kind=L['kind'], d=L['path'].d(prec))
    if L['kind'] == 'stroke':
        d['strokeWidth'] = L['sw']
        d['linecap'] = L.get('cap', 'round')
        d['linejoin'] = L.get('join', 'round')
    return d


def layer_svg(L, prec=2):
    if L['kind'] == 'stroke':
        return (f'<path d="{L["path"].d(prec)}" stroke="currentColor" stroke-width="{fmt(L["sw"], 3)}" '
                f'stroke-linecap="{L.get("cap", "round")}" stroke-linejoin="{L.get("join", "round")}"/>')
    return f'<path d="{L["path"].d(prec)}" fill="currentColor"/>'


def svg_doc(vb, layers, title, extra='', attrs=''):
    w, h = vb[2], vb[3]
    body = ''.join(layer_svg(L) for L in layers)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vbstr(vb)}" width="{fmt(w, 2)}" height="{fmt(h, 2)}" '
            f'fill="none"{attrs}><title>{title}</title>{extra}{body}</svg>\n')


def fit_vb(layers, margin):
    mins, maxs = [], []
    for L in layers:
        mn, mx = L['path'].bbox()
        m = margin + (L['sw'] / 2 if L['kind'] == 'stroke' else 0)
        mins.append(mn - m)
        maxs.append(mx + m)
    mn = np.min(mins, 0)
    mx = np.max(maxs, 0)
    return (float(mn[0]), float(mn[1]), float(mx[0] - mn[0]), float(mx[1] - mn[1]))


def normalize(layers, margin=0.0, round_to=1.0):
    """translate layers so the viewBox starts at 0,0 with whole-number size"""
    vb = fit_vb(layers, margin)
    w = math.ceil(vb[2] / round_to) * round_to
    h = math.ceil(vb[3] / round_to) * round_to
    dx = -vb[0] + (w - vb[2]) / 2
    dy = -vb[1] + (h - vb[3]) / 2
    out = [dict(L, path=L['path'].translate(dx, dy)) for L in layers]
    return out, (0.0, 0.0, float(w), float(h))


files = {}


def put(name, text):
    files[name] = text
    with open(os.path.join(OUT, name), 'w') as f:
        f.write(text)


# ---------------------------------------------------------------------------
# 1. arches
# ---------------------------------------------------------------------------
arches = O.arches()
clip_defs = []
J = {}
for key, a in arches.items():
    cid = f'md-arch-{key}'
    dclip = a['clip'].d(4)
    clip_defs.append(f'<clipPath id="{cid}" clipPathUnits="objectBoundingBox"><path d="{dclip}"/></clipPath>')
    put(f'arch-{key}-clip.svg',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" preserveAspectRatio="none" width="200" height="300">'
        f'<title>{a["label"]} - clip / mask (objectBoundingBox 0..1)</title>'
        f'<defs><clipPath id="{cid}" clipPathUnits="objectBoundingBox"><path d="{dclip}"/></clipPath></defs>'
        f'<path d="{dclip}" fill="currentColor"/></svg>\n')
    for L in a['outline']:
        L['join'] = 'miter'
        L['cap'] = 'butt'
    put(f'arch-{key}-outline.svg', svg_doc((0, 0, O.AW, O.AH), a['outline'], f'{a["label"]} - outline'))
    J[f'arch-{key}'] = dict(
        label=a['label'],
        files=dict(clip=f'arch-{key}-clip.svg', outline=f'arch-{key}-outline.svg'),
        clip=dict(clipPathUnits='objectBoundingBox', viewBox='0 0 1 1', id=cid, d=dclip,
                  note='drawn for a 2:3 portrait box; other ratios stretch the arch'),
        px=dict(viewBox='0 0 200 300', d=a['px'].d(2)),
        outline=dict(viewBox='0 0 200 300', layers=[layer_json(L) for L in a['outline']],
                     note='outer line inset by half its weight so it sits on the clip edge; hairline 9 units inside'))
put('arch-clippaths.svg',
    '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true">'
    f'<defs>{"".join(clip_defs)}</defs></svg>\n')

# ---------------------------------------------------------------------------
# 2. whiplash
# ---------------------------------------------------------------------------
W = O.whiplash()
wl_stroke = [dict(kind='stroke', sw=O.SW, path=W['path'])]
wl_fill = [dict(kind='fill', sw=0, path=W['taper'])]
h_stroke, vb_hs = normalize(wl_stroke, margin=0.5)
# tapered: same placement as the stroked one so they are interchangeable
mn, _ = W['path'].bbox()
dx = h_stroke[0]['path'].bbox()[0][0] - mn[0]
dy = h_stroke[0]['path'].bbox()[0][1] - mn[1]
h_fill = [dict(L, path=L['path'].translate(dx, dy)) for L in wl_fill]
put('whiplash-h.svg', svg_doc(vb_hs, h_stroke, 'Whiplash line - horizontal', attrs=' preserveAspectRatio="xMinYMax meet"'))
put('whiplash-h-tapered.svg', svg_doc(vb_hs, h_fill, 'Whiplash line - horizontal, tapered', attrs=' preserveAspectRatio="xMinYMax meet"'))
# vertical: curl at the top, tail running down
v_stroke, vb_vs = normalize([dict(L, path=L['path'].rotate(90)) for L in wl_stroke], margin=0.5)
mn0 = W['path'].rotate(90).bbox()[0]
mn1 = v_stroke[0]['path'].bbox()[0]
v_fill = [dict(L, path=L['path'].rotate(90).translate(*(mn1 - mn0))) for L in wl_fill]
put('whiplash-v.svg', svg_doc(vb_vs, v_stroke, 'Whiplash line - vertical', attrs=' preserveAspectRatio="xMidYMin meet"'))
put('whiplash-v-tapered.svg', svg_doc(vb_vs, v_fill, 'Whiplash line - vertical, tapered', attrs=' preserveAspectRatio="xMidYMin meet"'))
# symmetric centred divider: two whiplashes tail to tail, a jewel between
gap = 12.0
left = W['path'].translate(-gap, 0)            # tail end was at (0,0); curl to the left
right = left.mirror_x(0)
jewel = Path().circle((0, 0), 2.4)
for k in (-1, 1):
    jewel.circle((k * 6.6, 0), 1.1)
div_layers, vb_div = normalize([dict(kind='stroke', sw=O.SW, path=Path().extend(left).extend(right)),
                                dict(kind='fill', sw=0, path=jewel)], margin=0.5)
put('whiplash-divider.svg', svg_doc(vb_div, div_layers, 'Whiplash divider - symmetric'))
lt = W['taper'].translate(-gap, 0)
divt_layers = [dict(kind='fill', sw=0, path=Path().extend(lt).extend(lt.mirror_x(0)).extend(jewel))]
shift = div_layers[1]['path'].bbox()[0] - jewel.bbox()[0]
divt_layers = [dict(L, path=L['path'].translate(*shift)) for L in divt_layers]
put('whiplash-divider-tapered.svg', svg_doc(vb_div, divt_layers, 'Whiplash divider - symmetric, tapered'))
for name, vb, layers, lab in [('whiplash-h', vb_hs, h_stroke, 'Whiplash, horizontal (curl left, tail runs out to the right)'),
                              ('whiplash-h-tapered', vb_hs, h_fill, 'Whiplash, horizontal, tapered fill'),
                              ('whiplash-v', vb_vs, v_stroke, 'Whiplash, vertical (curl top, tail runs down)'),
                              ('whiplash-v-tapered', vb_vs, v_fill, 'Whiplash, vertical, tapered fill'),
                              ('whiplash-divider', vb_div, div_layers, 'Whiplash divider, symmetric'),
                              ('whiplash-divider-tapered', vb_div, divt_layers, 'Whiplash divider, symmetric, tapered')]:
    J[name] = dict(label=lab, file=name + '.svg', viewBox=vbstr(vb), layers=[layer_json(L) for L in layers])
J['whiplash-h']['note'] = ('curvature-continuous curve (Euler-spiral curl); tail is dead level at the bottom-right '
                           'so it can continue as a CSS rule')

# ---------------------------------------------------------------------------
# 3. secession border
# ---------------------------------------------------------------------------
tile, (tw, th) = O.secession_tile()
tile_l = [dict(kind='fill', sw=0, path=tile)]
put('secession-border-tile.svg', svg_doc((0, 0, tw, th), tile_l, 'Secession border - repeat tile (repeat-x)'))
tile_v = tile.affine([[0, -1, th], [1, 0, 0]])          # rotate 90deg: bars become horizontal
put('secession-border-tile-v.svg', svg_doc((0, 0, th, tw), [dict(kind='fill', sw=0, path=tile_v)],
                                           'Secession border - repeat tile, vertical (repeat-y)'))
n_rep = 12
strip = Path()
for i in range(n_rep):
    strip.extend(tile.translate(i * tw, 0))
put('secession-border.svg', svg_doc((0, 0, tw * n_rep, th), [dict(kind='fill', sw=0, path=strip)],
                                    'Secession border - 12-tile strip'))
pil, (pw, ph) = O.secession_pilaster()
put('secession-pilaster.svg', svg_doc((0, 0, pw, ph), [dict(kind='fill', sw=0, path=pil)], 'Secession pilaster panel'))
J['secession-border-tile'] = dict(label='Secession border tile (Moser bars with circles + Hoffmann squares); seamless in x',
                                  file='secession-border-tile.svg', viewBox=f'0 0 {fmt(tw, 2)} {fmt(th, 2)}',
                                  layers=[layer_json(L) for L in tile_l],
                                  css='background: url(secession-border-tile.svg) repeat-x left center / auto 100%;')
J['secession-border-tile-v'] = dict(label='Same tile rotated for vertical borders; seamless in y',
                                    file='secession-border-tile-v.svg', viewBox=f'0 0 {fmt(th, 2)} {fmt(tw, 2)}',
                                    layers=[dict(kind='fill', d=tile_v.d())])
J['secession-border'] = dict(label='12-tile strip', file='secession-border.svg', viewBox=f'0 0 {fmt(tw * n_rep, 2)} {fmt(th, 2)}')
J['secession-pilaster'] = dict(label='Secession pilaster (vertical panel)', file='secession-pilaster.svg',
                               viewBox=f'0 0 {fmt(pw, 2)} {fmt(ph, 2)}', layers=[dict(kind='fill', d=pil.d())])

# ---------------------------------------------------------------------------
# 4. stem & bloom
# ---------------------------------------------------------------------------
sl, (sw_, sh) = O.sunflower_stem()
put('stem-sunflower.svg', svg_doc((0, 0, sw_, sh), sl, 'Stem and bloom - stylised sunflower'))
J['stem-sunflower'] = dict(label='Stylised sunflower on a long stem, whiplash leaves, root curls',
                           file='stem-sunflower.svg', viewBox=f'0 0 {fmt(sw_, 2)} {fmt(sh, 2)}',
                           layers=[layer_json(L) for L in sl])

# ---------------------------------------------------------------------------
# 5. corners
# ---------------------------------------------------------------------------
cl, (cw, ch) = O.corner()
put('corner-loop.svg', svg_doc((0, 0, cw, ch), cl, 'Corner flourish - looped rule (top-left; mirror for the others)'))
J['corner-loop'] = dict(label='Corner flourish: the frame rule ties a teardrop loop (top-left)',
                        file='corner-loop.svg', viewBox=f'0 0 {fmt(cw, 2)} {fmt(ch, 2)}',
                        layers=[layer_json(L) for L in cl],
                        frame=dict(main_rule_inset=O.CO['y0'], hairline_inset=O.CO['y0'] + O.CO['gap'],
                                   note='rules leave the box at the right and bottom edges; continue them with 1.5 / 0.75 lines'),
                        mirror=dict(top_right='scale(-1,1)', bottom_left='scale(1,-1)', bottom_right='scale(-1,-1)'))
c2, (c2w, c2h) = O.corner_secession()
put('corner-secession.svg', svg_doc((0, 0, c2w, c2h), c2, 'Corner - Secession crossing rules with checker (top-left)'))
J['corner-secession'] = dict(label='Geometric corner: rules cross and overshoot, checker in the cut-off square (top-left)',
                             file='corner-secession.svg', viewBox=f'0 0 {fmt(c2w, 2)} {fmt(c2h, 2)}',
                             layers=[layer_json(L) for L in c2],
                             frame=dict(main_rule_inset=22, hairline_inset=28),
                             mirror=dict(top_right='scale(-1,1)', bottom_left='scale(1,-1)', bottom_right='scale(-1,-1)'))

# ---------------------------------------------------------------------------
# 6. halo
# ---------------------------------------------------------------------------
hl, (hw, hh) = O.halo()
put('halo-sunburst.svg', svg_doc((0, 0, hw, hh), hl, 'Halo / sunburst - sits behind the circular logo'))
J['halo-sunburst'] = dict(label='Radiating halo: 24 bundles of 3 fine rays, jewel dots, inner ring',
                          file='halo-sunburst.svg', viewBox=f'0 0 {fmt(hw, 2)} {fmt(hh, 2)}',
                          layers=[layer_json(L) for L in hl],
                          logo=dict(center=[200, 200], radius=100, note='logo diameter = half the halo box; inner ring r=112'))

meta = dict(
    kit='M/darbnica - Jugendstil / Secession ornament kit (new retro direction)',
    colour='every SVG uses currentColor; set CSS color on the parent (inline SVG or mask-image) - '
           'as an <img> it renders black',
    weights=dict(main=O.SW, hairline=O.HAIR, halo_rays=1.0,
                 note='weights are in each ornament\'s own units; most are drawn to be used at roughly 1:1 to 2:1 px'),
    path_commands='M L C Z only (arcs converted to cubic beziers) so every path works in SVG, Path2D, Figma and clip-path',
    clip_usage=dict(
        inline='<svg width=0 height=0><defs>...arch-clippaths.svg...</defs></svg>  then  img{clip-path:url(#md-arch-ogee)}',
        mask='img{-webkit-mask:url(arch-ogee-clip.svg) center/100% 100% no-repeat;mask:url(arch-ogee-clip.svg) center/100% 100% no-repeat}'),
    palette=dict(ink='#1F1D1A', paper='#EFE9DD', cream='#F4E9D8', green='#22382D'),
)
with open(os.path.join(OUT, 'ornaments.json'), 'w') as f:
    json.dump(dict(meta=meta, ornaments=J), f, indent=1, ensure_ascii=False)

# keep the in-memory layers for the preview
PREVIEW = dict(arches=arches, h_stroke=(vb_hs, h_stroke), h_fill=(vb_hs, h_fill), v_stroke=(vb_vs, v_stroke),
               v_fill=(vb_vs, v_fill), div=(vb_div, div_layers), divt=(vb_div, divt_layers), tile=((0, 0, tw, th), tile_l),
               tile_v=((0, 0, th, tw), [dict(kind='fill', sw=0, path=tile_v)]), pil=((0, 0, pw, ph), [dict(kind='fill', sw=0, path=pil)]),
               sun=((0, 0, sw_, sh), sl), corner=((0, 0, cw, ch), cl), corner2=((0, 0, c2w, c2h), c2), halo=((0, 0, hw, hh), hl),
               clip_defs=''.join(clip_defs))
print('wrote', len(files), 'svg files to', OUT)
