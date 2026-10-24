"""Halftone masters (black dots on transparent) in the style of work/ear/halftone.py, with centroid-snapped dots
for partially covered cells so thin parts (tubes, ropes, keys) survive the screen.
python3 -I ht.py [names...]"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *

PAD = 24
LONG = 1400

# tone parameters per instrument (F-variant defaults; ear-like screen)
BASE = dict(cell=11, clahe=2.0, grid=8, gamma=1.6, loc=1.2, sig=14, s_curve=0.8, base=0.04, span=0.92,
            edge=0.35, rim=5.0, lo_p=1, hi_p=98, blur=1.5, ke=0.5, esig=1.2, ep=93)
TP = {
    'sax':      dict(),
    'trumpet':  dict(gamma=1.4),
    'trombone': dict(gamma=1.5),
    'bass':     dict(gamma=1.2, ke=0.4),
    'clarinet': dict(gamma=1.1, ke=0.45, s_curve=0.5),
    'drum':     dict(gamma=1.1, ke=0.45, s_curve=0.5),
    'cymbals':  dict(gamma=1.4, ke=0.2, blur=4.0, loc=0.5, clahe=1.2),
}
TP = {k_: dict(BASE, **v) for k_, v in TP.items()}


def load_cut(name, long=LONG):
    im = cv2.imread(W + f'cutfull_{name}.png', cv2.IMREAD_UNCHANGED)
    s = (long - 2 * PAD) / max(im.shape[:2])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    im = cv2.copyMakeBorder(im, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    a = im[..., 3].astype(np.float32) / 255
    bgr = im[..., :3].copy()
    for _ in range(2):
        bgr = cv2.bilateralFilter(bgr, 9, 16, 7)
    L = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    return L, a


def tone_map(L, a, clahe=2.0, grid=8, gamma=1.6, loc=1.2, sig=14, s_curve=0.8, base=0.04, span=0.92, edge=0.35,
             rim=5.0, lo_p=1, hi_p=98, blur=1.5, ke=0.5, esig=1.2, ep=93, invert=False, **_):
    m = a > 0.5
    Lm = L.copy(); Lm[~m] = np.median(L[m])
    if clahe:
        cl = cv2.createCLAHE(clipLimit=clahe, tileGridSize=(grid, grid))
        Lm = cl.apply(np.clip(Lm, 0, 255).astype(np.uint8)).astype(np.float32)
    Lb = cv2.GaussianBlur(Lm, (0, 0), blur) if blur else Lm
    lo, hi = np.percentile(Lb[m], [lo_p, hi_p])
    d = np.clip((hi - Lb) / (hi - lo), 0, 1)
    if invert:
        d = 1 - d
    d = d ** gamma
    d = np.clip(d + loc * (d - cv2.GaussianBlur(d, (0, 0), sig)), 0, 1)
    if s_curve:
        d = (1 - s_curve) * d + s_curve * (d * d * (3 - 2 * d))
    t = base + span * d
    if ke:
        Ls = cv2.GaussianBlur(Lm, (0, 0), esig)
        g = np.sqrt(cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3) ** 2 + cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3) ** 2)
        g = np.clip(g / np.percentile(g[m], ep), 0, 1)
        t = t + ke * cv2.GaussianBlur(g, (0, 0), 1.2)
    dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    t = t + edge * np.exp(-dist / rim)
    return np.clip(t, 0, 0.97) * a


def screen(T, M, cell=13.0, angle=45, seed=1, rough=0.35, jit=0.06, snap=(0.85, 0.45)):
    """AM screen. Full cells: dot at the lattice point sized by the sampled tone (as in the ear).
    Partly covered cells (mask fraction < snap[0]): dot moves toward the darkness centroid and its area
    tends to the cell's darkness mass, so thin features keep a row of dots on them."""
    h, w = T.shape
    th = np.deg2rad(angle); c, s = np.cos(th), np.sin(th)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx * c + yy * s) / cell; v = (-xx * s + yy * c) / cell
    iu = np.floor(u).astype(np.int64); iv = np.floor(v).astype(np.int64)
    iu0, iv0 = iu.min() - 2, iv.min() - 2
    nu, nv = iu.max() - iu0 + 3, iv.max() - iv0 + 3
    idx = ((iu - iu0) * nv + (iv - iv0)).ravel()
    n = nu * nv
    TM = (T * (M > 0.02)).ravel().astype(np.float64)
    S = np.bincount(idx, TM, n); Sx = np.bincount(idx, TM * xx.ravel(), n); Sy = np.bincount(idx, TM * yy.ravel(), n)
    A = np.bincount(idx, (M.ravel() > 0.5).astype(np.float64), n)
    cu = (np.arange(n) // nv + iu0 + 0.5).astype(np.float64); cv_ = (np.arange(n) % nv + iv0 + 0.5).astype(np.float64)
    X = (cu * c - cv_ * s) * cell; Y = (cu * s + cv_ * c) * cell
    Xi = np.clip(X, 0, w - 1).astype(np.float32).reshape(nu, nv); Yi = np.clip(Y, 0, h - 1).astype(np.float32).reshape(nu, nv)
    Tc = cv2.remap(T.astype(np.float32), Xi, Yi, cv2.INTER_LINEAR).ravel().astype(np.float64)
    Mc = cv2.remap(M.astype(np.float32), Xi, Yi, cv2.INTER_LINEAR).ravel().astype(np.float64)
    inside = (X >= 0) & (X < w) & (Y >= 0) & (Y < h)
    Tc[~inside] = 0; Mc[~inside] = 0
    frac = A / (cell * cell)
    wsn = np.clip((snap[0] - frac) / (snap[0] - snap[1]), 0, 1)          # 0 = lattice dot, 1 = centroid dot
    cx = np.where(S > 1e-6, Sx / np.maximum(S, 1e-9), X); cy = np.where(S > 1e-6, Sy / np.maximum(S, 1e-9), Y)
    area_lat = Tc * cell * cell * (Mc > 0.5)
    area_cen = S
    area = (1 - wsn) * area_lat + wsn * area_cen
    PX = (1 - wsn) * X + wsn * cx; PY = (1 - wsn) * Y + wsn * cy
    hsh = np.sin(cu * 12.9898 + cv_ * 78.233) * 43758.5453; hsh = hsh - np.floor(hsh)
    R = np.sqrt(np.maximum(area, 0) / np.pi) * (1 + jit * (hsh * 2 - 1))
    rng = np.random.default_rng(seed)
    noise = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 1.2); noise /= noise.std() + 1e-6
    out = np.zeros((h, w), np.float32)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            j = ((iu + du - iu0) * nv + (iv + dv - iv0))
            px = PX[j].astype(np.float32); py = PY[j].astype(np.float32); r = R[j].astype(np.float32)
            d = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
            cov = np.clip(r - d + 0.5 + rough * noise, 0, 1) * (r > 0.35)
            out = np.maximum(out, cov)
    return out


def master(name, long=LONG, invert=False, **over):
    p = dict(TP[name]); p.update(over)
    L, a = load_cut(name, long)
    T = tone_map(L, a, invert=invert, **p)
    M = a
    cov = screen(T, M, cell=p['cell'], angle=45)
    k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    clip = cv2.GaussianBlur(cv2.dilate((a > 0.5).astype(np.float32), k9), (0, 0), 0.8)
    cov = cov * clip
    return cov, a


def save_dots(path, cov, hexcol='#000000', limit_kb=800):
    """Single-colour dots as an RGBA PNG (colour constant, coverage in alpha). Falls back to an equivalent
    palette PNG (index = alpha level, tRNS ramp) only if the RGBA file would exceed the size budget."""
    from PIL import Image
    a = np.round(np.clip(cov, 0, 1) * 255).astype(np.uint8)
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    rgba_ = np.zeros(a.shape + (4,), np.uint8); rgba_[..., 0] = r; rgba_[..., 1] = g; rgba_[..., 2] = b; rgba_[..., 3] = a
    Image.fromarray(rgba_, 'RGBA').save(path, optimize=True)
    if os.path.getsize(path) / 1024 <= limit_kb:
        return os.path.getsize(path) // 1024
    im = Image.fromarray(a, 'P')
    im.putpalette([r, g, b] * 256)
    im.save(path, optimize=True, transparency=bytes(range(256)))
    print('  (palette fallback)', os.path.basename(path))
    return os.path.getsize(path) // 1024


def rgba(cov, hexcol='#000000'):
    col = hex2bgr(hexcol)
    o = np.zeros(cov.shape + (4,), np.uint8)
    o[..., :3] = col.astype(np.uint8)
    o[..., 3] = np.round(np.clip(cov, 0, 1) * 255).astype(np.uint8)
    return o


if __name__ == '__main__':
    names = [n for n in sys.argv[1:] if n in INST] or list(INST)
    for name in names:
        cov, a = master(name)
        np.save(W + f'htcov_{name}.npy', cov)
        k1 = save_dots(OUT + f'afisa_{name}_halftone.png', cov, '#000000')
        k2 = save_dots(OUT + f'afisa_{name}_halftone_rose.png', cov, '#9E2F3A')
        covi, _ = master(name, invert=True)
        np.save(W + f'htcovi_{name}.npy', covi)
        k3 = save_dots(OUT + f'afisa_{name}_halftone_inv.png', covi, '#000000')
        print(name, cov.shape, k1, 'KB', k2, 'KB inv', k3, 'KB')
