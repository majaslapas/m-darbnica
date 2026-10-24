"""Two-colour stencils (+ optional line drawings) traced with potrace.
Canvas: SS x a 1400-long viewBox. python3 -I stencil.py [names...] [--trace]"""
import sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
from stx import base, smooth_bin, drop_small, show, two
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter1d

SS = 2


# ---------- primitives ----------
def suppress(big, it=4, d=11, sc=22, ss=9):
    x = big.copy()
    for _ in range(it):
        x = cv2.bilateralFilter(x, d, sc, ss)
    return x


def Lum(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * (100 / 255)


def stroke(canvas, pts, width, taper=(0, 0), closed=False):
    """Draw a polyline with round caps and optional tapering ends (fractions of length) onto a bool canvas."""
    P = np.asarray(pts, np.float64)
    if closed:
        P = np.vstack([P, P[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if d[-1] < 1:
        return canvas
    s = np.arange(0, d[-1], 1.5)
    X = np.interp(s, d, P[:, 0]); Y = np.interp(s, d, P[:, 1])
    Lt = d[-1]
    wv = np.full(len(s), width / 2.0)
    if taper[0]:
        wv = np.minimum(wv, width / 2 * (0.25 + 0.75 * np.clip(s / (taper[0] * Lt), 0, 1)))
    if taper[1]:
        wv = np.minimum(wv, width / 2 * (0.25 + 0.75 * np.clip((Lt - s) / (taper[1] * Lt), 0, 1)))
    c8 = canvas.astype(np.uint8)
    for x, y, r in zip(X, Y, wv):
        cv2.circle(c8, (int(round(x * 4)), int(round(y * 4))), max(int(round(r * 4)), 1), 1, -1, cv2.LINE_8, 2)
    return c8 > 0


def ellipse_pts(cx, cy, ax, ay, ang=0.0, t0=0, t1=360, n=240):
    t = np.deg2rad(np.linspace(t0, t1, n))
    a = np.deg2rad(ang)
    x = ax * np.cos(t); y = ay * np.sin(t)
    return np.stack([cx + x * np.cos(a) - y * np.sin(a), cy + x * np.sin(a) + y * np.cos(a)], 1)


def smooth_curve(P, sig=6, closed=False):
    P = np.asarray(P, np.float64)
    mode = 'wrap' if closed else 'nearest'
    return np.stack([gaussian_filter1d(P[:, 0], sig, mode=mode), gaussian_filter1d(P[:, 1], sig, mode=mode)], 1)


def catmull(P, step=2.0):
    P = np.array(P, float); P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(int(np.linalg.norm(p2 - p1) / step), 2)
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2]); return np.array(out)


def regions(L, m, thr, above=True, sig=2.0, open_r=2, close_r=3, min_area=300, inner_r=0):
    x = cv2.GaussianBlur(L, (0, 0), sig)
    b = (x > thr) if above else (x < thr)
    b &= m
    if inner_r:
        b &= cv2.erode(m.astype(np.uint8), k(inner_r)) > 0
    if open_r:
        b = cv2.morphologyEx(b.astype(np.uint8), cv2.MORPH_OPEN, k(open_r)) > 0
    if close_r:
        b = cv2.morphologyEx(b.astype(np.uint8), cv2.MORPH_CLOSE, k(close_r)) > 0
    return drop_small(b, min_area)


def long_edges(img, mask, lo, hi, minlen, margin=8):
    L8 = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0]
    e = cv2.Canny(L8, lo, hi, L2gradient=True) > 0
    inner = cv2.erode(mask.astype(np.uint8), k(margin)) > 0
    e &= inner
    lab, n = ndi.label(e, structure=np.ones((3, 3)))
    sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sz >= minlen
    return keep[lab]


def finish(S, cuts, smooth=1.6, min_solid=600, min_hole=250):
    st = S & ~cuts
    st = smooth_bin(st, smooth)
    st = drop_small(st, min_solid)
    st = ~drop_small(~st, min_hole)
    return st


def contour_smooth(bits, sigma, ss=4, min_len=20):
    """Smooth every outer and hole contour along its arc length, re-render with even-odd fill (supersampled)."""
    cs, hier = cv2.findContours(bits.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    h, w = bits.shape
    big = np.zeros((h * ss, w * ss), np.uint8)
    polys = []
    for c in cs:
        c = c[:, 0, :].astype(np.float64)
        if len(c) < min_len:
            continue
        sg = min(sigma, len(c) / 6.0)
        sm = np.stack([gaussian_filter1d(c[:, 0], sg, mode='wrap'), gaussian_filter1d(c[:, 1], sg, mode='wrap')], 1)
        polys.append(np.round((sm + 0.5) * ss - 0.5).astype(np.int32))
    # even-odd: XOR-fill each polygon
    for pl in polys:
        m = np.zeros_like(big); cv2.fillPoly(m, [pl], 1)
        big ^= m
    return cv2.resize(big.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA) > 0.5


# ---------- tracing ----------
def fmt(v, dec=1):
    t = ('%.' + str(dec) + 'f') % v
    if '.' in t:
        t = t.rstrip('0').rstrip('.')
    if t.startswith('0.'):
        t = t[1:]
    elif t.startswith('-0.'):
        t = '-' + t[2:]
    if t in ('-0', ''):
        t = '0'
    return t


def join_nums(nums):
    out = ''
    for n in nums:
        if out and not n.startswith('-') and not (n.startswith('.') and ('.' in out.split(' ')[-1].split('-')[-1] if out else False)):
            out += ' '
        out += n
    return out


def encode_paths(plist, sc, dec=1):
    """potrace curves -> compact SVG path data with relative commands (coordinates rounded first, so no drift)."""
    q = lambda v: round(v * sc, dec)
    parts = []
    for c in plist:
        sp = c.start_point
        cx, cy = q(sp.x), q(sp.y)
        parts.append('M' + join_nums([fmt(cx, dec), fmt(cy, dec)]))
        last = None
        for sg in c.segments:
            if sg.is_corner:
                pts = [(q(sg.c.x), q(sg.c.y)), (q(sg.end_point.x), q(sg.end_point.y))]
                for (x, y) in pts:
                    nums = [fmt(x - cx, dec), fmt(y - cy, dec)]
                    parts.append(('' if last == 'l' else 'l') + join_nums(nums) if last != 'l' else ' ' + join_nums(nums) if not nums[0].startswith('-') else join_nums(nums))
                    last = 'l'; cx, cy = x, y
            else:
                x1, y1, x2, y2, x, y = q(sg.c1.x), q(sg.c1.y), q(sg.c2.x), q(sg.c2.y), q(sg.end_point.x), q(sg.end_point.y)
                nums = [fmt(x1 - cx, dec), fmt(y1 - cy, dec), fmt(x2 - cx, dec), fmt(y2 - cy, dec), fmt(x - cx, dec), fmt(y - cy, dec)]
                body = join_nums(nums)
                if last == 'c':
                    parts.append(body if body.startswith('-') else ' ' + body)
                else:
                    parts.append('c' + body)
                last = 'c'; cx, cy = x, y
        parts.append('z')
    return ''.join(parts)


def trace_svg(bits, path, alphamax=1.0, opttol=0.4, turd=None, label='', dec=1):
    """bits: bool array at SS scale. Writes compact SVG in 1x units (viewBox = canvas/SS)."""
    import potrace
    t = time.time()
    h, w = bits.shape
    bm = potrace.Bitmap(~bits)
    plist = bm.trace(turdsize=turd if turd is not None else 40 * SS * SS, alphamax=alphamax,
                     opticurve=True, opttolerance=opttol)
    d = encode_paths(plist, 1.0 / SS, dec)
    nseg = sum(len(c.segments) for c in plist)
    vw, vh = fmt(w / SS), fmt(h / SS)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}">'
           f'<path fill="currentColor" fill-rule="evenodd" d="{d}"/></svg>\n')
    open(path, 'w').write(svg)
    print(os.path.basename(path), len(plist), 'subpaths', nseg, 'segs', round(len(svg) / 1024, 1), 'KB', round(time.time() - t, 1), 's')
    return len(svg)


# ---------- builders ----------
def prep(name):
    big, m, s, off = base(name)
    S = smooth_bin(m > 0.5, 3.0)
    return big, S


def disc(canvas, cx, cy, r):
    c8 = canvas.astype(np.uint8)
    cv2.circle(c8, (int(round(cx * 4)), int(round(cy * 4))), int(round(r * 4)), 1, -1, cv2.LINE_8, 2)
    return c8 > 0


def build_clarinet():
    """Clean tube silhouette + hand-placed key-work (see clageo.py, verified by overlay on the photo)."""
    import clageo as G
    big, S0 = prep('clarinet')
    # cylindrical joints: constant edges measured on key-free rows; photo outline kept for mouthpiece/barrel and bell
    h, w = S0.shape
    S = S0.copy()
    for (y0, y1, xl, xr) in [(350, 1345, 130, 248), (1345, 1392, 128, 250), (1392, 2313, 130, 244)]:
        S[y0:y1, :] = False
        S[y0:y1, xl:xr + 1] = True
    S = contour_smooth(S, 2.0)
    # every cup/ring keeps a solid rim (side keys become small bumps instead of notches)
    for x, y, r in G.CUPS + G.RINGS:
        S = disc(S, x, y, r + 6.0) | S
    for x, y, rx, ry in G.LOW_CUPS:
        e = np.zeros((h, w), np.uint8); cv2.ellipse(e, (x, y), (rx + 6, ry + 6), 0, 0, 360, 1, -1, cv2.LINE_8)
        S |= e > 0
    h, w = S.shape
    cut = np.zeros((h, w), bool)
    for y0, y1 in G.BANDS:
        cut[y0:y1 + 1, :] = True
    for y in G.LIGATURE:
        cut = stroke(cut, [(149, y), (227, y)], 5.0)
    for x, y, r in G.CUPS:
        cut = disc(cut, x, y, r - 1.0)
    for x, y, r in G.RINGS:
        ring = disc(np.zeros((h, w), bool), x, y, r + 3.0) & ~disc(np.zeros((h, w), bool), x, y, r - 4.5)
        cut |= ring
    for x, y, r in G.HOLES:
        cut |= disc(np.zeros((h, w), bool), x, y, r + 2.5) & ~disc(np.zeros((h, w), bool), x, y, r - 3.0)
    for x, y, rx, ry in G.LOW_CUPS:
        e = np.zeros((h, w), np.uint8); cv2.ellipse(e, (x, y), (rx - 1, ry - 1), 0, 0, 360, 1, -1, cv2.LINE_8)
        cut |= e > 0
    x, y, a, b = G.BADGE
    e = np.zeros((h, w), np.uint8); cv2.ellipse(e, (x, y), (a, b), 0, 0, 360, 1, -1, cv2.LINE_8)
    cut |= e > 0
    rod = np.zeros((h, w), bool)
    rod = stroke(rod, [(G.ROD_UP, 862), (G.ROD_UP, 1338)], 6.0)
    rod = stroke(rod, [(G.ROD_UP, 1398), (G.ROD_UP, 1728)], 6.0)
    centres = {round(y, 1): (x, r) for x, y, r in G.CUPS + G.RINGS}
    for y in G.ARM_Y_UP:
        x, r = centres[round(y, 1)]
        if x - r - 2 > G.ROD_UP + 4:
            rod = stroke(rod, [(G.ROD_UP, y), (x - r + 1, y)], 6.0)
    rod = stroke(rod, list(G.LOW_ROD), 6.0)
    for a_, b_ in G.LOW_ARMS:
        rod = stroke(rod, [a_, b_], 6.0)
    cut |= rod
    cut &= S
    np.save(W + 'cla_S.npy', S)
    return big, S, cut, dict(min_solid=150, min_hole=40, smooth=0.8)


def hessian_ridge(L, sig):
    Lg = cv2.GaussianBlur(L, (0, 0), sig)
    dxx = cv2.Sobel(Lg, cv2.CV_32F, 2, 0, ksize=3); dyy = cv2.Sobel(Lg, cv2.CV_32F, 0, 2, ksize=3)
    dxy = cv2.Sobel(Lg, cv2.CV_32F, 1, 1, ksize=3)
    tr = dxx + dyy; d = np.sqrt((dxx - dyy) ** 2 + 4 * dxy ** 2)
    l1 = (tr + d) / 2; l2 = (tr - d) / 2
    return np.where(l2 < 0, -l2, 0) * (np.abs(l1) < 0.6 * np.abs(l2)) * sig * sig


def build_drum():
    big, S = prep('drum')
    sm = suppress(big, 3)
    L = Lum(sm)
    S = contour_smooth(S, 7)
    light = regions(L, S, 47, True, sig=2.5, open_r=4, close_r=4, min_area=2500, inner_r=6)
    light = contour_smooth(light, 12)
    np.save(W + 'drum_light.npy', light); np.save(W + 'drum_S.npy', S)
    lines = np.load(W + 'drum_lines.npy'); tw = np.load(W + 'drum_twist.npy')
    rp = np.zeros(S.shape, bool)
    for x1, y1, x2, y2 in lines:
        rp = stroke(rp, [(x1, y1), (x2, y2)], 15.0)
    rp = stroke(rp, tw, 21.0)
    rp &= cv2.erode(S.astype(np.uint8), k(5)) > 0
    return big, S, light | rp, dict(min_solid=800, min_hole=600, smooth=1.2)


def body_only(S, r=60):
    b = cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_OPEN, k(r)) > 0
    lab, n = ndi.label(b)
    sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sz)))


def inset_line(region, inset, width):
    e = cv2.erode(region.astype(np.uint8), k(inset)) > 0
    hw = max(int(round(width / 2)), 1)
    return (cv2.dilate(e.astype(np.uint8), k(hw)) > 0) & ~(cv2.erode(e.astype(np.uint8), k(hw)) > 0)


def build_bass():
    big, S = prep('bass')
    sm = suppress(big, 3); L = Lum(sm)
    h, w = S.shape
    yy, xx = np.mgrid[0:h, 0:w]
    canvas = np.zeros((h, w), bool)
    # f-holes (dark, left and right of the strings)
    fz = ((xx < 318) | (xx > 445)) & (yy > 1640) & (yy < 2010)
    fh = regions(L, S & fz, 17, above=False, sig=1.2, open_r=1, close_r=3, min_area=600, inner_r=4)
    fh = ndi.binary_fill_holes(fh)
    # bridge (light wood)
    bz = (xx > 285) & (xx < 465) & (yy > 1805) & (yy < 1880)
    br = regions(L, S & bz, 48, above=True, sig=1.0, open_r=1, close_r=4, min_area=300)
    br = ndi.binary_fill_holes(br)
    # pegbox opening (dark)
    pz = (xx > 352) & (xx < 406) & (yy > 215) & (yy < 448)
    pb = regions(L, S & pz, 16, above=False, sig=2.0, open_r=2, close_r=6, min_area=300)
    pb = ndi.binary_fill_holes(pb)
    lines = canvas.copy()
    for a, b in [((357, 470), (331, 2036)), ((375, 470), (377, 2036)), ((391, 470), (405, 2036))]:
        lines = stroke(lines, [a, b], 4.6)
    lines = stroke(lines, [(348, 2062), (410, 2062), (393, 2374), (365, 2374)], 4.2, closed=True)
    body = body_only(S, 60)
    purf = inset_line(body, 17, 5)
    attach = cv2.dilate((S & ~(cv2.dilate(body.astype(np.uint8), k(3)) > 0)).astype(np.uint8), k(46)) > 0
    purf &= ~attach
    purf &= ~((xx > 300) & (xx < 460) & (yy < 1560))      # hidden under the fingerboard
    cuts = fh | br | pb | lines | purf
    return big, S, cuts, dict(min_solid=500, min_hole=200, smooth=1.4)


def streak_map(big, S, sigs, t, minlen, inner_r=6, el_min=5, supp=2):
    sm = suppress(big, supp); L = Lum(sm)
    R = np.max([hessian_ridge(L, s_) for s_ in sigs], 0)
    inner = cv2.erode(S.astype(np.uint8), k(inner_r)) > 0
    b = (R > t) & inner
    b = cv2.morphologyEx(b.astype(np.uint8), cv2.MORPH_CLOSE, k(2)) > 0
    lab, n = ndi.label(b, structure=np.ones((3, 3)))
    if not n:
        return b
    idx = range(1, n + 1)
    ys, xs = np.indices(lab.shape)
    mx = np.array(ndi.mean(xs, lab, idx)); my = np.array(ndi.mean(ys, lab, idx))
    vxx = np.array(ndi.mean(xs * xs, lab, idx)) - mx ** 2; vyy = np.array(ndi.mean(ys * ys, lab, idx)) - my ** 2
    vxy = np.array(ndi.mean(xs * ys, lab, idx)) - mx * my
    tr = vxx + vyy; det = vxx * vyy - vxy ** 2; disc = np.sqrt(np.maximum(tr ** 2 / 4 - det, 0))
    l1 = tr / 2 + disc; l2 = np.maximum(tr / 2 - disc, 1e-3)
    keep = np.zeros(n + 1, bool); keep[1:] = (np.sqrt(12 * l1) > minlen) & (np.sqrt(l1 / l2) > el_min)
    return keep[lab]


SAX_RINGS = [(952, 806, 42), (952, 917, 47), (957, 1057, 49), (945, 1226, 44), (962, 1386, 50),
             (965, 1712, 52), (962, 1848, 52), (975, 2072, 54), (955, 2265, 50)]


def build_sax():
    big, S = prep('sax')
    h, w = S.shape
    yy, xx = np.mgrid[0:h, 0:w]
    stk = streak_map(big, S, (2.5, 4), 8, 120)
    stk &= ~((xx > 845) & (xx < 1035) & (yy > 740) & (yy < 2360))    # key column: rings instead
    rings = np.zeros((h, w), bool)
    for cx, cy, r in SAX_RINGS:
        rings = stroke(rings, ellipse_pts(cx, cy, r, r), 7.0, closed=True)
    cuts = stk | rings
    return big, S, cuts, dict(min_solid=500, min_hole=200, smooth=1.4)


def build_trombone():
    big, S = prep('trombone')
    stk = streak_map(big, S, (2, 3), 6, 120)
    return big, S, stk, dict(min_solid=400, min_hole=200, smooth=1.3)


def build_trumpet():
    big, S = prep('trumpet')
    stk = streak_map(big, S, (2, 3), 6, 100)
    ln = np.zeros(S.shape, bool)
    ln = stroke(ln, [(1146, 370), (1432, 370)], 5.0)                 # casing tops under the main tube
    ln = stroke(ln, [(1146, 667), (1432, 667)], 5.0)                 # casing bottoms
    for x, segs in [(1238, [(372, 474), (598, 667)]), (1339, [(372, 518), (562, 667)])]:
        for y0, y1 in segs:
            ln = stroke(ln, [(x, y0), (x, y1)], 6.0)
    for (xa, xb, y) in [(827, 928, 436), (1032, 1145, 436), (835, 928, 513), (967, 1008, 513), (1062, 1145, 513)]:
        ln = stroke(ln, [(xa, y), (xb, y)], 7.0)                       # gaps between the tuning-slide tubes
    return big, S, stk | ln, dict(min_solid=400, min_hole=150, smooth=1.3)


def build_cymbals():
    big, S = prep('cymbals')
    h, w = S.shape
    cx, cy, ax, ay, ang = np.load(W + 'cym_front_ellipse.npy')
    inner = cv2.erode(S.astype(np.uint8), k(14)) > 0
    arc = np.zeros((h, w), bool)
    arc = stroke(arc, ellipse_pts(cx, cy, ax / 2, ay / 2, ang, n=900), 16.0, closed=True)
    arc &= inner
    dome = np.zeros((h, w), bool)
    dome = stroke(dome, ellipse_pts(1505, 1419, 610, 696, 0, n=700), 16.0, closed=True)
    sm = suppress(big, 2); L = Lum(sm)
    yy, xx = np.mgrid[0:h, 0:w]
    zone = (xx > 2020) & (xx < 2480) & (yy > 1080) & (yy < 1620)
    char = regions(L, S & zone, 24, above=False, sig=1.2, open_r=1, close_r=3, min_area=400)
    # hand-traced cloth strap (negative) with its fold kept as a solid line
    sp = smooth_curve(catmull(np.load(W + 'cym_strap.npy').tolist() + [np.load(W + 'cym_strap.npy')[0].tolist()], 3.0), 3, closed=True)
    strap = np.zeros((h, w), np.uint8)
    cv2.fillPoly(strap, [np.round(sp).astype(np.int32)], 1)
    strap = strap > 0
    fold = stroke(np.zeros((h, w), bool), smooth_curve(catmull(np.load(W + 'cym_fold.npy').tolist(), 3.0), 4), 14.0)
    strap &= ~fold
    gap = cv2.dilate(strap.astype(np.uint8), k(9)) > 0          # keep a solid margin between strap and dome ring
    dome &= ~gap
    return big, S, arc | dome | strap, dict(min_solid=800, min_hole=300, smooth=1.6)


BUILD = {'clarinet': build_clarinet, 'drum': build_drum, 'bass': build_bass, 'sax': build_sax, 'trombone': build_trombone, 'trumpet': build_trumpet, 'cymbals': build_cymbals}

TRACE = {'drum': dict(opttol=1.0, alphamax=1.15)}
CS = {'clarinet': 1.5}

if __name__ == '__main__':
    names = [n for n in sys.argv[1:] if n in INST] or list(BUILD)
    for name in names:
        big, S, cuts, fp = BUILD[name]()
        st = finish(S, cuts, **fp)
        st = contour_smooth(st, CS.get(name, 3.0))
        np.save(W + f'st_{name}.npy', st)
        H = 900 if big.shape[0] > big.shape[1] else 450
        show([big, two(st), two(st, (191, 214, 199)[::-1], (53, 69, 31)[::-1])], W + f'prev/st_{name}.jpg', H)
        if '--trace' in sys.argv:
            tp = TRACE.get(name, {})
            bits = st
            if tp.get('presmooth'):
                bits = smooth_bin(st, tp['presmooth'])
            trace_svg(bits, OUT + f'afisa_{name}_stencil.svg', alphamax=tp.get('alphamax', 1.1), opttol=tp.get('opttol', 0.8),
                      turd=tp.get('turd'))
