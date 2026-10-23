"""M/darbnica - Jugendstil / Secession ornament kit generator.
Every ornament is returned as {viewBox, layers:[{kind, sw, path}], ...}.
kind = 'stroke' (stroke=currentColor) or 'fill' (fill=currentColor)."""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geom import Path, integrate_curve, curve_to_path, sampled_to_path, TAU

SW = 1.5      # main line weight (in each ornament's own units, drawn ~1:1 px)
HAIR = 0.75   # hairline weight


def gauss_k(s, area, mu, sg):
    return area / (sg * math.sqrt(math.pi)) * np.exp(-((s - mu) / sg) ** 2)


def euler_ramp(s, s0, Lc, kmax, p=1.6):
    u = np.clip((s - s0) / Lc, 0, 1)
    return kmax * u ** p


# ---------------------------------------------------------------------------
# 1. ARCHES  (design space 200 x 300 = 2:3 portrait; bbox version = /200, /300)
# ---------------------------------------------------------------------------
AW, AH = 200.0, 300.0


def arch_round(d=0.0):
    r = 100 - d
    p = Path().M((d, AH - d)).L((d, 100))
    p.arc((100, 100), r, math.pi, 2 * math.pi)
    p.L((AW - d, AH - d)).Z()
    return p


HK_H = 71.0   # half width of the keyhole jambs


def arch_keyhole(d=0.0):
    R = 100 - d
    h = HK_H - d
    cy = 100
    a = math.acos(h / R)
    yj = cy + math.sqrt(R * R - h * h)
    p = Path().M((100 - h, AH - d)).L((100 - h, yj))
    p.arc((100, cy), R, math.pi - a, 2 * math.pi + a)
    p.L((100 + h, AH - d)).Z()
    return p


# ogee window: two square steps (12 x 12) at the shoulders, then convex+concave arcs
OG = dict(xs=24.0, ys=104.0, step=12.0, ya=0.0, th=math.radians(58), ph=math.radians(30))


def _ogee_solve():
    xs, ys, ya, th, ph = OG['xs'], OG['ys'], OG['ya'], OG['th'], OG['ph']
    dx, dy = 100 - xs, ys - ya
    A = np.array([[1 - math.cos(th), math.cos(th - ph) - math.cos(th)],
                  [math.sin(th), math.sin(th) - math.sin(th - ph)]])
    r1, r2 = np.linalg.solve(A, [dx, dy])
    c1 = np.array([xs + r1, ys])
    E1 = c1 + r1 * np.array([-math.cos(th), -math.sin(th)])
    c2 = E1 + r2 * (E1 - c1) / r1
    return r1, r2, c1, E1, c2


def arch_ogee(d=0.0):
    xs, ys, st = OG['xs'], OG['ys'], OG['step']
    r1, r2, c1, E1, c2 = _ogee_solve()
    # left half from bottom-centre to apex
    R1, R2 = r1 - d, r2 + d
    left = Path().M((100, AH - d)).L((d, AH - d)).L((d, ys + 2 * st + d)).L((st + d, ys + 2 * st + d))
    left.L((st + d, ys + st + d)).L((2 * st + d, ys + st + d)).L((xs + d, ys))
    a1s = math.pi
    a1e = math.pi + OG['th']
    left.arc(c1, R1, a1s, a1e)
    # arc 2 (concave) from its start angle to the apex on x = 100
    a2s = math.atan2(*(c1 - c2)[::-1])
    yap = c2[1] + math.sqrt(R2 * R2 - (100 - c2[0]) ** 2)
    a2e = math.atan2(yap - c2[1], 100 - c2[0])
    da = (a2e - a2s + math.pi) % TAU - math.pi
    left.arc(c2, R2, a2s, a2s + da)
    right = left.mirror_x(100).reversed_open()
    p = Path().M(left.subs[0][0])
    for seg in left.subs[0][1]:
        p.subs[-1][1].append(seg)
    for seg in right.subs[0][1]:
        p.subs[-1][1].append(seg)
    return p.Z()


def arches():
    out = {}
    for key, fn, label in [('round', arch_round, 'Tall round arch'),
                           ('keyhole', arch_keyhole, 'Horseshoe / keyhole arch'),
                           ('ogee', arch_ogee, 'Jugendstil ogee window, stepped shoulders')]:
        clip = fn(0).scale(1 / AW, 1 / AH)
        # outline: outer line sits just inside the edge, fine inner rule 8 units in
        outline = [dict(kind='stroke', sw=SW, path=fn(SW / 2)),
                   dict(kind='stroke', sw=HAIR, path=fn(9.0))]
        out[key] = dict(label=label, clip=clip, px=fn(0), outline=outline)
    return out


# ---------------------------------------------------------------------------
# 2. WHIPLASH
# ---------------------------------------------------------------------------
WH = dict(a1=0.36, mu1=300, sg1=100, sc0=460, Lc=170, kmax=0.135)


def whip_curve():
    w = WH
    L = w['sc0'] + w['Lc']

    def kap(s):
        return gauss_k(s, w['a1'], w['mu1'], w['sg1']) - euler_ramp(s, w['sc0'], w['Lc'], w['kmax'])
    s, pts, th = integrate_curve(kap, L, theta0=math.pi, n=6000)
    return s, pts, th


def _whip_knots(s):
    L = s[-1]
    # coarse on the long tail, finer in the curl
    a = np.linspace(0, WH['sc0'], 13)
    b = np.linspace(WH['sc0'], L, 15)[1:]
    return np.concatenate([a, b])


def whiplash():
    s, pts, th = whip_curve()
    p = curve_to_path(s, pts, th, knots=_whip_knots(s))
    # tapered (filled) variant: thin at the tail, full in the lash, fine in the curl
    L = s[-1]
    u = s / L
    wpk, upk = 2.75, 0.58
    w = np.where(u < upk, 0.35 + (wpk - 0.35) * np.exp(-((u - upk) / 0.26) ** 2),
                 0.85 + (wpk - 0.85) * np.exp(-((u - upk) / 0.20) ** 2))
    n = np.stack([-np.sin(th), np.cos(th)], 1)
    idx = np.linspace(0, len(s) - 1, 150).astype(int)
    # denser sampling in the curl
    idx = np.unique(np.concatenate([idx, np.linspace(int(len(s) * 0.7), len(s) - 1, 120).astype(int)]))
    A = pts[idx] + n[idx] * (w[idx, None] / 2)
    B = pts[idx] - n[idx] * (w[idx, None] / 2)
    tip = pts[-1] + np.array([math.cos(th[-1]), math.sin(th[-1])]) * 0.45
    tail = pts[0] - np.array([math.cos(th[0]), math.sin(th[0])]) * 0.2
    poly = np.concatenate([[tail], A, [tip], B[::-1]])
    taper = sampled_to_path(poly, closed=True)
    return dict(path=p, taper=taper, tail=pts[0], tail_dir=th[0], s=s, pts=pts, th=th)


# ---------------------------------------------------------------------------
# 3. SECESSION BORDER TILE   (tile 48 x 60, repeats seamlessly in x)
# ---------------------------------------------------------------------------
def secession_tile(W=48.0, H=60.0):
    f = Path()
    bw = 1.5
    # double rules top and bottom (full tile width so they join)
    f.rect(0, 0, W, bw)
    f.rect(0, 4.5, W, 0.75)
    f.rect(0, H - bw, W, bw)
    f.rect(0, H - 5.25, W, 0.75)
    top, bot = 5.25, H - 5.25
    # triplet of bars hanging from the inner rule, ending in circles (Moser)
    cx = 12.0
    for dx, ln, r in [(-5.5, 29, 1.9), (0, 37, 2.5), (5.5, 29, 1.9)]:
        x = cx + dx
        f.rect(x - bw / 2, top, bw, ln)
        f.circle((x, top + ln + r + 1.7), r)
    # a fine rod strung with three squares (Hoffmann), rule to rule
    sx = 36.0
    q = 5.0
    ys = [19.0, 27.5, 36.0]
    edges = [top] + sum([[y, y + q] for y in ys], []) + [bot]
    for y0, y1 in zip(edges[0::2], edges[1::2]):
        f.rect(sx - 0.375, y0, 0.75, y1 - y0)
    for y in ys:
        f.rect(sx - q / 2, y, q, q)
    return f, (W, H)


def secession_pilaster(W=44.0, H=360.0):
    f = Path()
    bw = 1.5
    cx = W / 2
    # frame: outer bars + cap and foot rules
    f.rect(0, 0, bw, H)
    f.rect(W - bw, 0, bw, H)
    f.rect(0, 0, W, bw)
    f.rect(0, 5, W, 0.75)
    f.rect(0, H - 5.75, W, 0.75)
    f.rect(0, H - bw, W, bw)
    # cap: 3x3 checker
    q = 4.4
    for r in range(3):
        for c in range(3):
            if (r + c) % 2 == 0:
                f.rect(cx - 1.5 * q + c * q, 12 + r * q, q, q)
    # three bars dropping from under the cap, ending in circles at staggered heights
    y0 = 12 + 3 * q + 6
    for dx, ln, rr in [(-8.5, 214, 2.1), (0, 262, 2.9), (8.5, 214, 2.1)]:
        x = cx + dx
        f.rect(x - bw / 2, y0, bw, ln)
        f.circle((x, y0 + ln + rr + 2.0), rr)
    # foot: column of squares under the long bar
    yb = y0 + 262 + 2 * 2.9 + 6
    for i in range(3):
        f.rect(cx - 2.2, yb + i * 8, 4.4, 4.4)
    return f, (W, H)


# ---------------------------------------------------------------------------
# 4. STEM & BLOOM (sunflower)  viewBox 120 x 440
# ---------------------------------------------------------------------------
def leaf(base, ang0, L, wmax, bend, curl=0.0):
    """leaf along an axis curve starting at base, initial heading ang0 (rad);
    returns (outline Path, midrib Path)."""
    def kap(s):
        return bend / L + gauss_k(s, curl, 0.9 * L, 0.1 * L)
    s, pts, th = integrate_curve(kap, L, theta0=ang0, p0=base, n=2000)
    u = s / L
    # width profile: narrow stalk, fullest ~40%, long point
    w = wmax * np.sin(np.pi * np.clip(u, 0, 1) ** 0.85) ** 1.6
    n = np.stack([-np.sin(th), np.cos(th)], 1)
    idx = np.linspace(0, len(s) - 1, 36).astype(int)
    A = pts[idx] + n[idx] * (w[idx, None] / 2)
    B = pts[idx] - n[idx] * (w[idx, None] / 2)
    poly = np.concatenate([A, B[::-1][1:-1]])
    outline = sampled_to_path(poly, closed=True)
    k0, k1 = int(len(s) * 0.12), int(len(s) * 0.74)
    mid = curve_to_path(s[k0:k1], pts[k0:k1], th[k0:k1], segs=6)
    return outline, mid


SF = dict(cy=64.0, disc=15.0, n=16, r0=19.5, r1=45.0, hw=5.4)


def sunflower_stem(W=120.0, H=440.0):
    cx, cy = W / 2, SF['cy']
    st = Path()
    hair = Path()
    fill = Path()
    # disc: ring, inner hairline ring, ring of seeds, centre
    st.circle((cx, cy), SF['disc'])
    hair.circle((cx, cy), 10.2)
    for k in range(10):
        a = TAU * k / 10
        fill.circle((cx + 6.2 * math.cos(a), cy + 6.2 * math.sin(a)), 0.95)
    fill.circle((cx, cy), 1.9)
    # petals: lens shapes, rotated so the stem passes between two petals
    n, r0, r1, hw = SF['n'], SF['r0'], SF['r1'], SF['hw']
    step = 360 / n
    for k in range(n):
        a = 90 + step / 2 + step * k
        loc = Path().M((r0, 0)).C((r0 + 5, -hw), (r1 - 11, -hw * 0.9), (r1, 0)) \
                    .C((r1 - 11, hw * 0.9), (r0 + 5, hw), (r0, 0)).Z()
        st.extend(loc.rotate(a).translate(cx, cy))
    # stem
    y_top = cy + SF['disc']
    y_bot = H - 30
    st.M((cx, y_top)).L((cx, y_bot))
    # big leaf pair: spring outward, sweep up, tips flick out (whiplash leaf)
    o, m = leaf((cx, 330.0), math.radians(-90 - 45), 104, 22, bend=0.9, curl=-0.7)
    for P in (o, o.mirror_x(cx)):
        st.extend(P)
    for P in (m, m.mirror_x(cx)):
        hair.extend(P)
    # small pair higher up
    o2, m2 = leaf((cx, 214.0), math.radians(-90 - 45), 50, 11, bend=0.9, curl=-0.7)
    for P in (o2, o2.mirror_x(cx)):
        st.extend(P)
    for P in (m2, m2.mirror_x(cx)):
        hair.extend(P)
    # foot: two root spirals curling outward and up, plus a seed dot
    def kap(s):
        return euler_ramp(s, 2, 44, 0.30, p=1.4)
    s, pts, th = integrate_curve(kap, 46, theta0=math.radians(112), p0=(cx, y_bot - 16), n=2000)
    kn = np.concatenate([np.linspace(0, 20, 4), np.linspace(20, 46, 10)[1:]])
    root = curve_to_path(s, pts, th, knots=kn)
    st.extend(root)
    st.extend(root.mirror_x(cx))
    fill.circle((cx, y_bot + 8), 2.4)
    layers = [dict(kind='stroke', sw=SW, path=st), dict(kind='stroke', sw=HAIR, path=hair),
              dict(kind='fill', sw=0, path=fill)]
    return layers, (W, H)


# ---------------------------------------------------------------------------
# 5. CORNER FLOURISH (top-left; 160 x 160; frame lines exit right & bottom)
#    main rule: a single line that ties itself into a teardrop loop at the corner
# ---------------------------------------------------------------------------
CO = dict(S=160.0, y0=40.0, p=2.0, tip=5.0, gap=6.0, notch=10.0)


def _loop_half(y0, Lc, p, S):
    f = lambda t: np.sin(np.pi / 2 * np.clip(t / Lc, 0, 1)) ** (2 * p)
    t = np.linspace(0, Lc, 4000)
    K = (3 * math.pi / 4) / np.trapezoid(f(t), t)
    s, pts, th = integrate_curve(lambda s: K * f(s), Lc, theta0=math.pi, p0=(0, 0), n=4000)
    dx, dy = pts[-1]
    x0 = y0 + dy - dx          # so that the loop tip lands on the diagonal
    pts = pts + np.array([x0, y0])
    half = Path().M((S, y0)).L((x0, y0))
    curve_to_path(s, pts, th, knots=np.linspace(0, Lc, 13), path=half, move=False)
    return half, pts[-1]


def loop_corner_line(S, y0, p, tip):
    h, _ = _loop_half(y0, 100.0, p, S)
    mn, _ = h.bbox()
    c = (y0 - mn[0]) / 100.0
    half, tip_pt = _loop_half(y0, (y0 - tip) / c, p, S)
    other = half.mirror_diag().reversed_open()
    P = Path().M(half.subs[0][0])
    P.subs[-1][1] += half.subs[0][1] + other.subs[0][1]
    return P, tip_pt


def _loop_eye(P, y0):
    # sample the closed loop (the part of the line beyond the crossing at (y0, y0))
    pts = []
    st, segs, _ = P.subs[0]
    cur = st
    for seg in segs:
        if seg[0] == 'C':
            t = np.linspace(0, 1, 30)[:, None]
            b = ((1 - t) ** 3) * cur + 3 * ((1 - t) ** 2) * t * seg[1] + 3 * (1 - t) * t * t * seg[2] + t ** 3 * seg[3]
            pts.extend(b)
        cur = seg[-1]
    pts = np.array(pts)
    loop = pts[(pts[:, 0] <= y0 + 1e-6) & (pts[:, 1] <= y0 + 1e-6)]
    x, y = loop[:, 0], loop[:, 1]
    a = x * np.roll(y, -1) - np.roll(x, -1) * y
    A = a.sum() / 2
    return np.array([((x + np.roll(x, -1)) * a).sum() / (6 * A), ((y + np.roll(y, -1)) * a).sum() / (6 * A)])


def corner():
    S, y0, g, R = CO['S'], CO['y0'], CO['gap'], CO['notch']
    main, tip = loop_corner_line(S, y0, CO['p'], CO['tip'])
    hair = Path()
    fill = Path()
    e = y0 + g
    hair.M((S, e)).L((e + R, e))
    hair.arc((e, e), R, 0, math.pi / 2)
    hair.L((e, S))
    fill.circle(_loop_eye(main, y0), 3.3)
    u = np.array([1, 1]) / math.sqrt(2)
    base = np.array([e, e]) + u * R
    fill.circle(base + u * 7.0, 1.7)
    layers = [dict(kind='stroke', sw=SW, path=main), dict(kind='stroke', sw=HAIR, path=hair),
              dict(kind='fill', sw=0, path=fill)]
    return layers, (S, S)


def corner_secession(S=120.0):
    """geometric alternative (Hoffmann): the rules cross and overshoot; the little
    square they cut off at the corner holds a checker."""
    main = Path()
    hair = Path()
    fill = Path()
    a, b = 22.0, 28.0          # main rule / hairline offsets from the box edge
    main.M((S, a)).L((3, a))
    main.M((a, S)).L((a, 3))
    hair.M((S, b)).L((b, b)).L((b, S))
    q = 4.0
    o = a - 3 - 3 * q          # checker sits in the cut-off square, 3 units off both rules
    for r in range(3):
        for c in range(3):
            if (r + c) % 2 == 0:
                fill.rect(o + c * q, o + r * q, q, q)
    layers = [dict(kind='stroke', sw=SW, path=main), dict(kind='stroke', sw=HAIR, path=hair),
              dict(kind='fill', sw=0, path=fill)]
    return layers, (S, S)


# ---------------------------------------------------------------------------
# 6. HALO / SUNBURST (400 x 400, logo sits in r <= 100)
# ---------------------------------------------------------------------------
def halo(S=400.0):
    c = np.array([S / 2, S / 2])
    hair = Path()
    main = Path()
    fill = Path()
    hair.circle(c, 112)
    nb = 24
    for b in range(nb):
        a0 = TAU * b / nb - math.pi / 2
        for j, (da, r_in, r_out) in enumerate([(-3.4, 122, 160), (0, 122, 186), (3.4, 122, 160)]):
            a = a0 + math.radians(da)
            d = np.array([math.cos(a), math.sin(a)])
            hair.M(c + d * r_in).L(c + d * r_out)
        d = np.array([math.cos(a0), math.sin(a0)])
        fill.circle(c + d * 193, 1.9)
        # small dot between bundles
        am = a0 + math.pi / nb
        dm = np.array([math.cos(am), math.sin(am)])
        fill.circle(c + dm * 150, 1.1)
    layers = [dict(kind='stroke', sw=1.0, path=hair), dict(kind='fill', sw=0, path=fill)]
    return layers, (S, S)
