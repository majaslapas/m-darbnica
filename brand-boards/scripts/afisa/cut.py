"""Instrument cutouts: chroma + luminance difference score -> watershed markers -> mask -> AA alpha + decontaminated RGBA.
python3 -I cut.py [names...]"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
from scipy import ndimage as ndi

WORK_LONG = 2400   # segmentation resolution (long side)
OUT_LONG = 1400    # cutout long side

# per-instrument settings (coordinates are fractions of the image: (x, y))
CFG = {
    'sax':      dict(wc=2.0, wl=1.0, shadow=0.25, t_hi=14, t_lo=5, fill=0.004, bg_pts=[], fg_polys=[]),
    'trumpet':  dict(wc=3.0, wl=1.0, shadow=0.2, t_hi=10, t_lo=4, fill=0.0, bg_pts=[], fg_polys=[]),
    'trombone': dict(wc=2.0, wl=1.0, shadow=0.25, t_hi=14, t_lo=5, fill=0.0, bg_pts=[], fg_polys=[]),
    'bass':     dict(wc=2.0, wl=1.0, shadow=0.3, t_hi=16, t_lo=6, fill=0.01, bg_pts=[], fg_polys=[]),
    'clarinet': dict(wc=2.0, wl=1.0, shadow=0.3, t_hi=16, t_lo=6, fill=0.01, bg_pts=[], fg_polys=[]),
    'drum':     dict(wc=0.0, wl=1.0, shadow=0.6, t_hi=14, t_lo=4, fill=0.2, bg_pts=[], fg_polys=[]),
    'cymbals':  dict(wc=3.0, wl=0.0, shadow=0.0, t_hi=12, t_lo=4, fill=0.2, bg_pts=[], fg_polys=[], chroma_only=True),
}


def bg_model(lab, init_bg, deg=4, iters=4):
    h, w = lab.shape[:2]
    sh, sw = 120, max(8, int(round(120 * w / h)))
    small = cv2.resize(lab, (sw, sh), interpolation=cv2.INTER_AREA)
    m = cv2.resize(init_bg.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_NEAREST) > 0
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float64)
    xx = xx / sw * 2 - 1; yy = yy / sh * 2 - 1
    A = np.stack([(xx ** i * yy ** j).ravel() for i in range(deg + 1) for j in range(deg + 1 - i)], 1)
    fit = np.zeros(small.shape, np.float64)
    use = m.ravel().copy()
    for _ in range(iters):
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A[use], small[..., c].ravel()[use], rcond=None)
            fit[..., c] = (A @ coef).reshape(sh, sw)
        d = np.sqrt(((small - fit) ** 2).sum(-1)).ravel()
        use = use & (d < max(np.percentile(d[use], 90) * 1.5, 2.0))
    return cv2.resize(fit.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def score_map(b, c):
    lab = cv2.cvtColor(cv2.GaussianBlur(b, (0, 0), 1.0).astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    h, w = lab.shape[:2]
    m = int(0.03 * max(h, w))
    border = np.zeros((h, w), bool); border[:m] = border[-m:] = True; border[:, :m] = border[:, -m:] = True
    med = np.median(lab[border], 0)
    d0 = np.sqrt(((lab - med) ** 2).sum(-1))
    bgm = bg_model(lab, d0 < np.percentile(d0[border], 95) + 4)
    dL = lab[..., 0] - bgm[..., 0]
    chroma = np.sqrt((lab[..., 1] - bgm[..., 1]) ** 2 + (lab[..., 2] - bgm[..., 2]) ** 2)
    if c.get('chroma_only'):
        chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    dLw = np.where(dL < 0, dL * c['shadow'], dL) * c['wl']
    S = np.sqrt(dLw ** 2 + (c['wc'] * chroma) ** 2)
    g = np.zeros((h, w), np.float32)
    for ch_ in range(3):
        gx = cv2.Sobel(lab[..., ch_], cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lab[..., ch_], cv2.CV_32F, 0, 1, ksize=3)
        g = np.maximum(g, np.sqrt(gx ** 2 + gy ** 2) * (1.0 if ch_ == 0 else 2.0))
    return S, g, lab, bgm


def poly_mask(shape, polys):
    h, w = shape
    m = np.zeros((h, w), np.uint8)
    for p in polys:
        pts = np.array([[x * w, y * h] for x, y in p], np.int32)
        cv2.fillPoly(m, [pts], 1)
    return m > 0


def segment(name):
    c = CFG[name]
    bgr = load_bgr(name)
    s = min(1.0, WORK_LONG / max(bgr.shape[:2]))
    b = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr.copy()
    h, w = b.shape[:2]
    S, g, lab, bgm = score_map(b, c)
    fgp = poly_mask((h, w), c['fg_polys'])
    sure_fg = (S > c['t_hi']) | fgp
    sure_fg = cv2.morphologyEx(sure_fg.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
    lowg = g < np.percentile(g, 60) * 1.5 + 2
    bgc = (S < c['t_lo']) & lowg & ~fgp
    bgc = cv2.erode(bgc.astype(np.uint8), k(2)) > 0
    lab_, n = ndi.label(bgc)
    sizes = ndi.sum(np.ones_like(lab_), lab_, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes > c.get('bg_min', 400) * (h * w) / (2400 * 1400)
    sure_bg = keep[lab_]
    markers = np.zeros((h, w), np.int32)
    markers[sure_bg] = 1
    markers[sure_fg & ~sure_bg] = 2
    sm = cv2.bilateralFilter(b, 7, 30, 5)
    cv2.watershed(sm, markers)
    fg = markers == 2
    # boundary pixels (-1) -> decide by score
    fg |= (markers == -1) & (S > (c['t_lo'] + c['t_hi']) / 2)
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
    # keep main components (>2% of largest)
    lab_, n = ndi.label(fg)
    if n:
        sizes = ndi.sum(np.ones_like(lab_), lab_, range(1, n + 1))
        keep = np.zeros(n + 1, bool); keep[1:] = sizes > sizes.max() * c.get('min_comp', 0.02)
        fg = keep[lab_]
    # fill holes up to fill*area(fg) unless they contain a bg hint point
    holes = ndi.binary_fill_holes(fg) & ~fg
    lab_, n = ndi.label(holes)
    if n:
        sizes = ndi.sum(np.ones_like(lab_), lab_, range(1, n + 1))
        protect = set()
        for (x, y) in c['bg_pts']:
            v = lab_[int(y * h), int(x * w)]
            if v: protect.add(v)
        fillv = np.zeros(n + 1, bool)
        for i in range(1, n + 1):
            fillv[i] = sizes[i - 1] <= c['fill'] * fg.sum() and i not in protect
        fg |= fillv[lab_]
    for (x, y) in c['bg_pts']:
        pass
    return b, fg, S, g


CFG2 = {
    # ch_*: chroma vs background; dark_*: dL below; bright_*: dL above; fill_px: max area (work px) of holes filled
    # unconditionally; bgish: holes with mean |dL|<bgish and mean chroma<1.5 are kept as background
    'sax':      dict(ch_hi=10, ch_lo=6.0, dark_hi=-50, dark_lo=-42, bright_hi=8, bright_lo=5, fill_px=60, bgish=4.0,
                     smooth_bg=True, sb_dl=-45, sb_g=1.1, sb_ch=2.5, grow=5, gr_ch=3.5,
                     hole_ch=4.5, hole_g=4.0, hole_frac=0.5),
    'trumpet':  dict(ch_hi=3.5, ch_lo=2.2, dark_hi=-24, dark_lo=-19, bright_hi=6, bright_lo=3, fill_px=400, bgish=3.0,
                     smooth_bg=True, sb_dl=-45, sb_g=1.1, sb_ch=1.6, grow=6),
    'trombone': dict(ch_hi=10, ch_lo=6.0, dark_hi=-50, dark_lo=-42, bright_hi=8, bright_lo=5, fill_px=150, bgish=4.0,
                     smooth_bg=True, sb_dl=-45, sb_g=1.1, sb_ch=2.5, grow=5, gr_ch=3.0),
    'bass':     dict(ch_hi=8, ch_lo=5.0, dark_hi=-45, dark_lo=-36, bright_hi=10, bright_lo=6, fill_px=400, bgish=4.0,
                     smooth_bg=True, sb_dl=-40, sb_g=1.1, sb_ch=2.0, grow=4, gr_ch=2.5),
    'clarinet': dict(ch_hi=8, ch_lo=5.0, dark_hi=-40, dark_lo=-30, bright_hi=8, bright_lo=5, fill_px=300, bgish=4.0,
                     smooth_bg=True, sb_dl=-35, sb_g=1.1, sb_ch=2.0, grow=4, gr_ch=2.5),
    'drum':     dict(ch_hi=99, ch_lo=99, dark_hi=-30, dark_lo=-14, bright_hi=99, bright_lo=99, fill_px=10**9, bgish=0,
                     seed_dl=-10),
    'cymbals':  dict(ch_hi=7, ch_lo=3.5, dark_hi=-99, dark_lo=-99, bright_hi=99, bright_lo=99, fill_px=10**9, bgish=0,
                     chroma_only=True, smooth_bg=True, sb_ch=2.2, sb_g=1.2, sb_dl=-999, grow=10, gr_ch=2.6, gr_g=2.2, gr_dl=-999),
}
HINTS = {k_: dict(bg_pts=[], fg_polys=[], bg_polys=[], bg_seeds=[]) for k_ in CFG2}
HINTS['drum']['bg_seeds'] = [(0.115, 0.30), (0.122, 0.30), (0.113, 0.55), (0.118, 0.55), (0.890, 0.30), (0.880, 0.60)]
HINTS['trumpet']['dark_boxes'] = [(0.4372, 0.436, 0.4468, 0.618, 32), (0.4695, 0.436, 0.4815, 0.618, 32),
                                  (0.333, 0.468, 0.414, 0.492, 38), (0.333, 0.518, 0.414, 0.538, 38),
                                  (0.355, 0.556, 0.414, 0.618, 62), (0.5065, 0.436, 0.514, 0.618, 62)]
HINTS['drum']['bg_seed_boxes'] = [(0.10, 0.12, 0.13, 0.84), (0.87, 0.12, 0.90, 0.84)]


def segment2(name, gc=True):
    c = CFG2[name]; hn = HINTS[name]
    bgr = load_bgr(name)
    s = min(1.0, WORK_LONG / max(bgr.shape[:2]))
    b = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr.copy()
    h, w = b.shape[:2]
    lab = cv2.cvtColor(cv2.GaussianBlur(b, (0, 0), 0.8).astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    m = int(0.03 * max(h, w))
    border = np.zeros((h, w), bool); border[:m] = border[-m:] = True; border[:, :m] = border[:, -m:] = True
    med = np.median(lab[border], 0)
    d0 = np.sqrt(((lab - med) ** 2).sum(-1))
    bgm = bg_model(lab, d0 < np.percentile(d0[border], 95) + 4)
    dL = lab[..., 0] - bgm[..., 0]
    if c.get('chroma_only'):
        ch = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    else:
        ch = np.sqrt((lab[..., 1] - bgm[..., 1]) ** 2 + (lab[..., 2] - bgm[..., 2]) ** 2)
    L = lab[..., 0]
    gm = np.sqrt(cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3) ** 2 + cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3) ** 2) / 4.0
    strong = (ch > c['ch_hi']) | (dL < c['dark_hi']) | (dL > c['bright_hi'])
    weak = (ch > c['ch_lo']) | (dL < c['dark_lo']) | (dL > c['bright_lo'])
    fgp = poly_mask((h, w), hn['fg_polys']); bgp = poly_mask((h, w), hn['bg_polys'])
    strong |= fgp; weak |= fgp
    strong = cv2.morphologyEx(strong.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
    lab_, n = ndi.label(weak)
    hit = np.zeros(n + 1, bool); hit[np.unique(lab_[strong])] = True; hit[0] = False
    fg = hit[lab_] & ~bgp
    if c.get('smooth_bg'):
        sb = (ch < c.get('sb_ch', 1.5)) & (gm < c.get('sb_g', 0.9)) & (dL > c.get('sb_dl', -30))
        sb = cv2.morphologyEx(sb.astype(np.uint8), cv2.MORPH_OPEN, k(c.get('sb_r', 3))) > 0
        lab2, n2 = ndi.label(sb)
        if n2:
            sz2 = ndi.sum(np.ones_like(lab2), lab2, range(1, n2 + 1))
            kp = np.zeros(n2 + 1, bool); kp[1:] = sz2 > c.get('sb_area', 150)
            sb = kp[lab2]
        fg &= ~sb
        np.save(W + f'sb_{name}.npy', sb)
    if c.get('grow'):
        sl = (ch < c.get('gr_ch', 1.7)) & (dL > c.get('gr_dl', -48)) & (gm < c.get('gr_g', 2.5))
        bgm_ = ~fg
        for _ in range(c['grow']):
            bgm_ = bgm_ | ((cv2.dilate(bgm_.astype(np.uint8), k(1)) > 0) & sl)
        fg = ~bgm_
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, k(2)) > 0
    fg = keep_near_main(fg, c)
    seeds = list(hn.get('bg_seeds', []))
    cand_b = (ch < c.get('seed_ch', 2.0)) & (dL > c.get('seed_dl', -10))
    for (bx0, by0, bx1, by1) in hn.get('bg_seed_boxes', []):
        yy_, xx_ = np.where(cand_b[int(by0 * h):int(by1 * h), int(bx0 * w):int(bx1 * w)])
        seeds += [((x_ + int(bx0 * w)) / w, (y_ + int(by0 * h)) / h) for y_, x_ in zip(yy_[::3], xx_[::3])]
    flood = seed_flood(seeds, ch, dL, gm, c, (h, w))
    fg &= ~flood
    fg = fill_holes(fg, dL, ch, gm, c, dict(bg_pts=hn['bg_pts'] + hn.get('bg_seeds', []), fg_polys=[]), (h, w))
    fg &= ~flood
    fg0 = fg.copy()
    if gc:
        fg = grabcut_refine(b, fg, fgp, bgp, c, hn, dL, ch)
        fg &= ~flood
        fg = keep_near_main(fg, c)
    if hn.get('dark_boxes'):
        Labs = lab[..., 0]; cha = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
        dark = np.zeros((h, w), bool)
        for x0_, y0_, x1_, y1_, lm in hn['dark_boxes']:
            X0, Y0, X1, Y1 = int(x0_ * w), int(y0_ * h), int(x1_ * w), int(y1_ * h)
            sub = (Labs[Y0:Y1, X0:X1] < lm) & (cha[Y0:Y1, X0:X1] < 4)
            dark[Y0:Y1, X0:X1] |= cv2.morphologyEx(sub.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
        fg &= ~dark
        fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
    return b, fg, fg0, dL, ch


def keep_near_main(fg, c, maxdist=None):
    lab_, n = ndi.label(fg)
    if not n:
        return fg
    sz = ndi.sum(np.ones_like(lab_), lab_, range(1, n + 1))
    main = lab_ == (1 + int(np.argmax(sz)))
    md = maxdist if maxdist is not None else c.get('near', 40)
    dist = cv2.distanceTransform((~main).astype(np.uint8), cv2.DIST_L2, 5)
    mind = ndi.minimum(dist, lab_, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = (sz > max(sz.max() * c.get('min_comp', 0.0005), 30)) & (mind < md)
    return keep[lab_]


def seed_flood(seeds, ch, dL, gm, c, shape):
    h, w = shape
    out = np.zeros((h, w), bool)
    if not seeds:
        return out
    cand = ((ch < c.get('seed_ch', 2.0)) & (dL > c.get('seed_dl', -10)) & (gm < c.get('seed_g', 99))).astype(np.uint8)
    lab_, n = ndi.label(cand)
    vals = set()
    for (x, y) in seeds:
        X, Y = min(int(round(x * w)), w - 1), min(int(round(y * h)), h - 1)
        win = lab_[max(Y - 2, 0):Y + 3, max(X - 2, 0):X + 3]
        vals.update(int(v) for v in np.unique(win) if v)
    if vals:
        sel = np.zeros(n + 1, bool); sel[list(vals)] = True
        out = sel[lab_]
    return out


def fill_holes(fg, dL, ch, gm, c, hn, shape):
    """Fill enclosed holes unless they look like real background (mostly neutral + smooth) or carry a bg hint."""
    h, w = shape
    holes = ndi.binary_fill_holes(fg) & ~fg
    lab_, n = ndi.label(holes)
    if not n:
        return fg
    idx = range(1, n + 1)
    sz = ndi.sum(np.ones_like(lab_), lab_, idx)
    bgpix = ((ch < c.get('hole_ch', 1.8)) & (np.abs(dL) < c.get('hole_dl', 40)) & (gm < c.get('hole_g', 6.0))).astype(np.float32)
    frac = ndi.mean(bgpix, lab_, idx)
    protect = set(int(lab_[int(y * h), int(x * w)]) for (x, y) in hn['bg_pts'])
    fillv = np.zeros(n + 1, bool)
    for i in idx:
        if i in protect:
            continue
        fillv[i] = sz[i - 1] <= c['fill_px'] or frac[i - 1] < c.get('hole_frac', 0.6)
    return fg | fillv[lab_]


def grabcut_refine(b, fg, fgp, bgp, c, hn, dL, ch):
    h, w = fg.shape
    sc = min(1.0, 1600 / max(h, w))
    bs = cv2.resize(b, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    f = cv2.resize(fg.astype(np.uint8), (bs.shape[1], bs.shape[0]), interpolation=cv2.INTER_NEAREST)
    mask = np.full(f.shape, cv2.GC_BGD, np.uint8)
    mask[cv2.dilate(f, k(6)) > 0] = cv2.GC_PR_BGD
    mask[f > 0] = cv2.GC_PR_FGD
    mask[cv2.erode(f, k(2)) > 0] = cv2.GC_FGD
    fs = cv2.resize(fgp.astype(np.uint8), (bs.shape[1], bs.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    bsm = cv2.resize(bgp.astype(np.uint8), (bs.shape[1], bs.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    mask[fs] = cv2.GC_FGD; mask[bsm] = cv2.GC_BGD
    bgd = np.zeros((1, 65)); fgd = np.zeros((1, 65))
    cv2.grabCut(bs, mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    g = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.float32)
    g = cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    # GrabCut may only remove pixels that look like background (neutral, bg-like luminance) and add thin rims
    bgl = (ch < 2.0) & (np.abs(dL) < 30)
    out = np.where(fg & ~g & bgl, False, fg)
    out |= g & (cv2.dilate(fg.astype(np.uint8), k(3)) > 0)
    out = cv2.morphologyEx(out.astype(np.uint8), cv2.MORPH_OPEN, k(1)) > 0
    lab_, n = ndi.label(out)
    if n:
        sz = ndi.sum(np.ones_like(lab_), lab_, range(1, n + 1))
        keep = np.zeros(n + 1, bool); keep[1:] = sz > max(sz.max() * 0.004, 50)
        out = keep[lab_]
    return fill_holes(out, dL, ch, c, HINTS_FILLCFG(c), (h, w)) if False else out


def HINTS_FILLCFG(c):
    return dict(bg_pts=[])


def guided_filter(I, p, r, eps):
    mean = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = mean(I), mean(p)
    cov = mean(I * p) - mI * mp
    var = mean(I * I) - mI * mI
    a = cov / (var + eps); bb = mp - a * mI
    return mean(a) * I + mean(bb)


def make_cutout(name, b, fg, inset=0.6, feather=0.9, ss_sigma=1.0, long=OUT_LONG, pad=8):
    h, w = fg.shape
    ys, xs = np.where(fg)
    so = long / max(ys.max() - ys.min() + 1, xs.max() - xs.min() + 1)
    pw = int(np.ceil(pad / so)) + 2
    y0, y1 = max(ys.min() - pw, 0), min(ys.max() + pw + 1, h)
    x0, x1 = max(xs.min() - pw, 0), min(xs.max() + pw + 1, w)
    fgc = fg[y0:y1, x0:x1]; bc = b[y0:y1, x0:x1]
    f = cv2.GaussianBlur(fgc.astype(np.float32), (0, 0), ss_sigma)
    ow, oh = int(round((x1 - x0) * so)), int(round((y1 - y0) * so))
    interp = cv2.INTER_AREA if so < 1 else cv2.INTER_CUBIC
    a = np.clip(cv2.resize(f, (ow, oh), interpolation=interp), 0, 1)
    col = np.clip(cv2.resize(bc.astype(np.float32), (ow, oh), interpolation=interp), 0, 255)
    hard = (a > 0.5).astype(np.uint8)
    din = cv2.distanceTransform(hard, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform(1 - hard, cv2.DIST_L2, 5)
    sd = np.where(hard > 0, din - 0.5, -(dout - 0.5))
    alpha = np.clip((sd - inset) / feather + 0.5, 0, 1)
    core = (sd > inset + 2.0).astype(np.float32)
    num = cv2.GaussianBlur(col * core[..., None], (0, 0), 2.5); den = cv2.GaussianBlur(core, (0, 0), 2.5)[..., None]
    ext = num / np.maximum(den, 1e-4)
    t = np.clip((inset + 2.5 - sd) / 2.5, 0, 1)[..., None]
    colo = np.where(den > 1e-3, col * (1 - t) + ext * t, col)
    rgba = np.dstack([np.clip(colo, 0, 255), alpha * 255]).round().astype(np.uint8)
    yy, xx = np.where(alpha > 0.004)
    Y0, Y1, X0, X1 = max(yy.min() - pad, 0), min(yy.max() + pad + 1, oh), max(xx.min() - pad, 0), min(xx.max() + pad + 1, ow)
    rgba = rgba[Y0:Y1, X0:X1]
    rgba[rgba[..., 3] == 0, :3] = 0
    # geometry: output px = (work px - (x0,y0)) * so - (X0,Y0)
    return rgba, (x0, y0, so, X0, Y0)


def premul_resize(bgra, s):
    f = bgra.astype(np.float32); a = f[..., 3:] / 255
    pm = np.dstack([f[..., :3] * a, f[..., 3:]])
    h, w = bgra.shape[:2]
    r = cv2.resize(pm, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA)
    a2 = np.maximum(r[..., 3:] / 255, 1e-6)
    rgb = np.where(r[..., 3:] > 0.5, r[..., :3] / a2, 0)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(r[..., 3:], 0, 255)]).round().astype(np.uint8)


def save_png(path, rgba, limit_kb=800):
    """BGRA -> RGBA PNG; over budget -> dithered palette PNG (palpng); still over -> premultiplied downscale."""
    cv2.imwrite(path, rgba, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if os.path.getsize(path) / 1024 <= limit_kb:
        return os.path.getsize(path) / 1024, 'rgba'
    import palpng
    im, s = rgba, 1.0
    while True:
        palpng.save_pal_rgba(path, cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA))
        kb = os.path.getsize(path) / 1024
        if kb <= limit_kb or s < 0.6:
            return kb, f'pal-dither scale {s:.2f} {im.shape[1]}x{im.shape[0]}'
        s *= 0.93
        im = premul_resize(rgba, s)


def check_sheet(name, b, fg, rgba):
    h, w = fg.shape
    ov = b.copy()
    cs, _ = cv2.findContours(fg.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(ov, cs, -1, (0, 0, 255), max(1, int(2 * max(h, w) / 2400)))
    so = 900 / max(h, w)
    ov = cv2.resize(ov, None, fx=so, fy=so, interpolation=cv2.INTER_AREA)
    tiles = [ov]
    for bgc in [(17, 17, 17), (106, 96, 216), (234, 241, 244)]:
        r = rgba.astype(np.float32)
        sc = ov.shape[0] / r.shape[0] if r.shape[0] / ov.shape[0] > r.shape[1] / ov.shape[1] else ov.shape[1] / r.shape[1]
        r = cv2.resize(r, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        canvas = np.zeros(ov.shape, np.float32); canvas[:] = bgc
        a = r[..., 3:] / 255
        y0 = (canvas.shape[0] - r.shape[0]) // 2; x0 = (canvas.shape[1] - r.shape[1]) // 2
        canvas[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r[..., :3] * a + canvas[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] * (1 - a)
        tiles.append(canvas.astype(np.uint8))
    if ov.shape[1] > ov.shape[0]:
        sheet = np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0)
    else:
        sheet = np.concatenate(tiles, 1)
    cv2.imwrite(W + f'prev/cut_{name}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])


if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if a in INST] or list(INST)
    for name in names:
        b, fg, fg0, dL, ch = segment2(name, gc='nogc' not in sys.argv)
        np.save(W + f'fg_{name}.npy', fg); np.save(W + f'fg0_{name}.npy', fg0)
        cv2.imwrite(W + f'work_{name}.png', b)
        if os.path.exists(W + f'work_{name}_rt.png'):          # retouched photo (see retouch.py) feeds all derivatives
            b = cv2.imread(W + f'work_{name}_rt.png')
        rgba, (x0, y0, so, X0, Y0) = make_cutout(name, b, fg)
        json.dump(dict(x0=int(x0), y0=int(y0), so=so, X0=int(X0), Y0=int(Y0), work_shape=list(fg.shape)), open(W + f'geom_{name}.json', 'w'))
        cv2.imwrite(W + f'cutfull_{name}.png', rgba)
        kb, mode = save_png(OUT + f'afisa_{name}_cut.png', rgba)
        check_sheet(name, b, fg, rgba)
        print(name, 'work', fg.shape, 'cut', rgba.shape, int(kb), 'KB', mode)
