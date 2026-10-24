"""Hand-placed drum lacing (stencil canvas coords) + ridge snapping."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *

T = {1: (156, 180), 2: (277, 241), 3: (710, 313), 4: (1360, 361), 5: (2048, 349), 6: (2505, 301), 7: (2662, 229)}
G = {0: (156, 1011), 1: (481, 1203), 2: (1047, 1155), 3: (1651, 1191), 4: (2337, 1155), 5: (2674, 1023)}
B = {0: (84, 1913), 1: (373, 2142), 2: (963, 2310), 3: (1663, 2334), 4: (2277, 2202), 5: (2626, 1949)}
V = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5), (4, 5), (4, 6), (5, 6), (5, 7)]   # (tug, top)
TWIST = [(650, 433), (794, 517), (963, 578), (1203, 631), (1350, 686), (1494, 674), (1711, 645), (1952, 602),
         (2144, 554), (2361, 493), (2505, 433), (2577, 409)]


def ropes_approx():
    lines = []
    for g, t in V:
        lines.append(('v', G[g], T[t]))
    for g in G:
        lines.append(('d', G[g], B[g]))
    return lines


def sample_mean(R, p0, p1, n=None):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    L = np.hypot(*(p1 - p0)); n = n or max(int(L / 3), 8)
    t = np.linspace(0.08, 0.92, n)       # ignore the ends (knots, tugs)
    xs = (p0[0] + (p1[0] - p0[0]) * t).astype(np.float32); ys = (p0[1] + (p1[1] - p0[1]) * t).astype(np.float32)
    v = cv2.remap(R, xs.reshape(1, -1), ys.reshape(1, -1), cv2.INTER_LINEAR)[0]
    return float(np.mean(np.minimum(v, np.percentile(v, 90))))


def snap(R, p0, p1, rad=36, step=4, iters=3):
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    offs = np.arange(-rad, rad + 1, step)
    best = sample_mean(R, p0, p1)
    for _ in range(iters):
        for which in (0, 1):
            cur = p0 if which == 0 else p1
            bb, bp = best, cur.copy()
            for dx in offs:
                for dy in offs:
                    cand = cur + (dx, dy)
                    sc = sample_mean(R, cand, p1) if which == 0 else sample_mean(R, p0, cand)
                    if sc > bb:
                        bb, bp = sc, cand
            if which == 0:
                p0 = bp
            else:
                p1 = bp
            best = bb
    return p0, p1, best


def project(p, a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); p = np.asarray(p, float)
    d = b - a; t = ((p - a) @ d) / (d @ d)
    return a + t * d


def final_lines(R):
    """Snap each rope's line, then clip it at the projections of the hand anchors."""
    out = []
    for g, t in V:
        a, b = G[g], T[t]
        p0, p1, sc = snap(R, a, b, rad=30, step=3)
        out.append(('v', project(a, p0, p1), project(b, p0, p1)))
    Rb = cv2.GaussianBlur(R, (0, 0), 6.0)
    for g in G:
        a, b = (G[g][0], G[g][1] + 40), B[g]
        p0, p1, sc = snap(Rb, a, b, rad=24, step=3)
        A = project((G[g][0], G[g][1] + 20), p0, p1); Bp = project(B[g], p0, p1)
        d = Bp - A; n = np.array([-d[1], d[0]]) / np.hypot(*d)
        out.append(('d', A + n * 11, Bp + n * 4))
        out.append(('d', A - n * 11, Bp - n * 4))
    return out


def twist_curve(R):
    pts = []
    for (x, y) in TWIST:
        best = (-1, y)
        for dy in range(-40, 41, 2):
            v = R[int(y + dy) - 2:int(y + dy) + 3, int(x) - 20:int(x) + 21].mean()
            if v > best[0]:
                best = (v, y + dy)
        pts.append((x, best[1]))
    P = np.array(pts, float)
    c = np.polyfit(P[:, 0], P[:, 1], 4)
    xs = np.linspace(P[0, 0], P[-1, 0], 200)
    return np.stack([xs, np.polyval(c, xs)], 1)
