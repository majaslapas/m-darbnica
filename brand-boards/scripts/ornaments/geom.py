"""Small geometry kit: paths made only of M / L / C / Z so they work everywhere
(SVG clipPath, CSS mask, Figma import, canvas Path2D)."""
import math
import numpy as np

TAU = 2 * math.pi


def fmt(v, prec):
    s = f"{v:.{prec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


class Path:
    """A list of subpaths; each subpath = [start, [seg...], closed]
    seg = ('L', p) or ('C', c1, c2, p); points are np arrays."""

    def __init__(self):
        self.subs = []

    # --- building -------------------------------------------------------
    def M(self, p):
        self.subs.append([np.array(p, float), [], False])
        return self

    @property
    def cur(self):
        s = self.subs[-1]
        return s[1][-1][-1] if s[1] else s[0]

    def L(self, p):
        self.subs[-1][1].append(("L", np.array(p, float)))
        return self

    def C(self, c1, c2, p):
        self.subs[-1][1].append(("C", np.array(c1, float), np.array(c2, float), np.array(p, float)))
        return self

    def Z(self):
        self.subs[-1][2] = True
        return self

    def arc(self, c, r, a0, a1):
        """circular arc around c from angle a0 to a1 (radians, SVG y-down coords),
        as cubic beziers. Assumes the current point is already on the arc start."""
        c = np.array(c, float)
        sweep = a1 - a0
        n = max(1, int(math.ceil(abs(sweep) / (math.pi / 2) - 1e-9)))
        d = sweep / n
        k = 4 / 3 * math.tan(d / 4)
        for i in range(n):
            t0 = a0 + i * d
            t1 = t0 + d
            p0 = c + r * np.array([math.cos(t0), math.sin(t0)])
            p1 = c + r * np.array([math.cos(t1), math.sin(t1)])
            c1 = p0 + k * r * np.array([-math.sin(t0), math.cos(t0)])
            c2 = p1 - k * r * np.array([-math.sin(t1), math.cos(t1)])
            self.C(c1, c2, p1)
        return self

    def circle(self, c, r):
        c = np.array(c, float)
        self.M(c + [r, 0])
        self.arc(c, r, 0, TAU)
        return self.Z()

    def rect(self, x, y, w, h):
        return self.M((x, y)).L((x + w, y)).L((x + w, y + h)).L((x, y + h)).Z()

    def hermite(self, pts, tans):
        """smooth chain through pts with tangent vectors tans (derivative wrt the
        parameter, already scaled so that segment i spans one parameter unit)."""
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            self.C(p0 + tans[i] / 3, p1 - tans[i + 1] / 3, p1)
        return self

    def extend(self, other):
        for s in other.subs:
            self.subs.append([s[0].copy(), [tuple(x if isinstance(x, str) else x.copy() for x in seg) for seg in s[1]], s[2]])
        return self

    # --- transforms -----------------------------------------------------
    def map(self, f):
        out = Path()
        for st, segs, cl in self.subs:
            ns = []
            for seg in segs:
                ns.append((seg[0],) + tuple(f(p) for p in seg[1:]))
            out.subs.append([f(st), ns, cl])
        return out

    def affine(self, m):
        m = np.array(m, float)  # 2x3

        def f(p):
            return m[:, :2] @ p + m[:, 2]
        return self.map(f)

    def translate(self, dx, dy):
        return self.affine([[1, 0, dx], [0, 1, dy]])

    def scale(self, sx, sy=None, cx=0, cy=0):
        sy = sx if sy is None else sy
        return self.affine([[sx, 0, cx - sx * cx], [0, sy, cy - sy * cy]])

    def rotate(self, deg, cx=0, cy=0):
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        return self.affine([[ca, -sa, cx - ca * cx + sa * cy], [sa, ca, cy - sa * cx - ca * cy]])

    def mirror_x(self, cx):
        return self.affine([[-1, 0, 2 * cx], [0, 1, 0]])

    def mirror_y(self, cy):
        return self.affine([[1, 0, 0], [0, -1, 2 * cy]])

    def mirror_diag(self):
        """swap x<->y (mirror about the line y = x)"""
        return self.affine([[0, 1, 0], [1, 0, 0]])

    def reversed_open(self):
        """reverse every subpath's direction (for chaining mirrored halves)"""
        out = Path()
        for st, segs, cl in self.subs:
            pts = [st] + [s[-1] for s in segs]
            ns = []
            for i in range(len(segs) - 1, -1, -1):
                seg = segs[i]
                start = pts[i]
                if seg[0] == "L":
                    ns.append(("L", start.copy()))
                else:
                    ns.append(("C", seg[2].copy(), seg[1].copy(), start.copy()))
            out.subs.append([pts[-1].copy(), ns, cl])
        return out

    # --- output ---------------------------------------------------------
    def d(self, prec=2):
        out = []

        def P(p):
            return fmt(p[0], prec) + " " + fmt(p[1], prec)
        for st, segs, cl in self.subs:
            out.append("M" + P(st))
            for seg in segs:
                if seg[0] == "L":
                    out.append("L" + P(seg[1]))
                else:
                    out.append("C" + P(seg[1]) + " " + P(seg[2]) + " " + P(seg[3]))
            if cl:
                out.append("Z")
        return "".join(out)

    def bbox(self):
        pts = []
        for st, segs, cl in self.subs:
            pts.append(st)
            for seg in segs:
                pts.extend(seg[1:])
        a = np.array(pts)
        return a.min(0), a.max(0)


def integrate_curve(kappa_fn, L, theta0=0.0, p0=(0, 0), n=4000):
    """curve from curvature kappa(s) (s in [0, L]); returns s, pts (n,2), theta"""
    s = np.linspace(0, L, n)
    k = kappa_fn(s)
    ds = s[1] - s[0]
    theta = theta0 + np.concatenate([[0], np.cumsum((k[1:] + k[:-1]) / 2 * ds)])
    dx = np.cos(theta)
    dy = np.sin(theta)
    x = p0[0] + np.concatenate([[0], np.cumsum((dx[1:] + dx[:-1]) / 2 * ds)])
    y = p0[1] + np.concatenate([[0], np.cumsum((dy[1:] + dy[:-1]) / 2 * ds)])
    return s, np.stack([x, y], 1), theta


def curve_to_path(s, pts, theta, segs=24, path=None, move=True, knots=None):
    """fit a sampled arc-length curve with Hermite cubics at `segs` knots
    (knots can be given explicitly as arc-length values)."""
    if knots is None:
        knots = np.linspace(s[0], s[-1], segs + 1)
    idx = [int(np.argmin(np.abs(s - kk))) for kk in knots]
    path = path or Path()
    P = [pts[i] for i in idx]
    if move:
        path.M(P[0])
    for a, b in zip(idx[:-1], idx[1:]):
        h = s[b] - s[a]
        t0 = np.array([math.cos(theta[a]), math.sin(theta[a])]) * h
        t1 = np.array([math.cos(theta[b]), math.sin(theta[b])]) * h
        path.C(pts[a] + t0 / 3, pts[b] - t1 / 3, pts[b])
    return path


def sampled_to_path(pts, closed=False, path=None, move=True):
    """Catmull-Rom (centripetal-ish uniform) through points -> cubic beziers."""
    pts = np.asarray(pts, float)
    n = len(pts)
    path = path or Path()
    if move:
        path.M(pts[0])
    rng = range(n if closed else n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i] - (pts[i + 1] - pts[i])
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2 + (p2 - p1)
        path.C(p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6, p2)
    if closed:
        path.Z()
    return path
