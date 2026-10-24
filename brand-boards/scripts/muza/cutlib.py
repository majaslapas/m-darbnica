"""Cutout + grading library for the Muza asset set (imported by run scripts in this dir)."""
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi

# ---------------- palette ----------------
HEX = dict(cream="#EFE7D8", green="#1F3A2D", rose="#D9A6A1", deeprose="#B65A61",
           ink="#151413", brass="#A9844E")


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


PAL = {k: hex2rgb(v) for k, v in HEX.items()}


# ---------------- colour helpers ----------------
def srgb2lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def lin2oklab(c):
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
    lms = c @ M1.T
    return np.cbrt(lms) @ M2.T


def oklab2lin(l):
    M2i = np.array([[1.0, 0.3963377774, 0.2158037573],
                    [1.0, -0.1055613458, -0.0638541728],
                    [1.0, -0.0894841775, -1.2914855480]], np.float32)
    M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                    [-1.2684380046, 2.6097574011, -0.3413193965],
                    [-0.0041960863, -0.7034186147, 1.7076147010]], np.float32)
    lms = (l @ M2i.T) ** 3
    return lms @ M1i.T


def luminance(rgb):
    lin = srgb2lin(rgb)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    return np.cbrt(np.clip(Y, 0, 1))  # perceptual-ish lightness 0..1


# ---------------- grading ----------------
def levels(L, alpha=None, lo_p=0.8, hi_p=99.6, lo_v=None, hi_v=None):
    m = (alpha > 0.9) if alpha is not None else np.ones(L.shape, bool)
    vals = L[m] if m.sum() > 100 else L.ravel()
    lo = np.percentile(vals, lo_p) if lo_v is None else lo_v
    hi = np.percentile(vals, hi_p) if hi_v is None else hi_v
    return np.clip((L - lo) / max(hi - lo, 1e-4), 0, 1)


def scurve(x, k=0.0, gamma=1.0):
    x = np.clip(x, 0, 1) ** gamma
    if k:
        s = x * x * (3 - 2 * x)
        x = (1 - k) * x + k * s
    return x


def duotone(rgb, dark, light, alpha=None, gamma=1.0, k=0.25, lo_p=0.8, hi_p=99.6, mid=None):
    """Map perceptual lightness onto an OKLab gradient dark->light (optionally via a mid stop)."""
    L = levels(luminance(rgb), alpha, lo_p, hi_p)
    t = scurve(L, k, gamma)[..., None]
    a = lin2oklab(srgb2lin(dark[None, None, :]))
    b = lin2oklab(srgb2lin(light[None, None, :]))
    if mid is None:
        lab = a + (b - a) * t
    else:
        m = lin2oklab(srgb2lin(mid[None, None, :]))
        t1 = np.clip(t * 2, 0, 1); t2 = np.clip(t * 2 - 1, 0, 1)
        lab = np.where(t < 0.5, a + (m - a) * t1, m + (b - m) * t2)
    return np.clip(lin2srgb(oklab2lin(lab)), 0, 1).astype(np.float32)


def warm_natural(rgb, alpha=None, sat=0.88, warmth=0.035, lift=None, top=None, k=0.12, gamma=1.0,
                 lo_p=0.3, hi_p=99.8):
    """Warm 'natural marble' grade: stays photographic. Black point lifted toward ink, white point
    rolled toward a warm off-white so it sits on cream without glare."""
    ink = PAL["ink"] if lift is None else lift
    white = np.array([0.975, 0.955, 0.915], np.float32) if top is None else top
    x = rgb.astype(np.float32)
    # warm white balance (in linear light)
    lin = srgb2lin(x)
    lin = lin * np.array([1 + warmth, 1.0, 1 - 1.6 * warmth], np.float32)
    x = lin2srgb(lin)
    # gentle saturation trim (in OKLab)
    lab = lin2oklab(srgb2lin(x))
    lab[..., 1:] *= sat
    x = lin2srgb(oklab2lin(lab))
    # tonal levels + mild S on lightness
    L = luminance(x)
    Ln = scurve(levels(L, alpha, lo_p, hi_p), k, gamma)
    ratio = (Ln + 1e-4) / (L + 1e-4)
    lab = lin2oklab(srgb2lin(x))
    lab[..., 0] = lab[..., 0] * np.clip(ratio, 0, 3)
    x = lin2srgb(oklab2lin(lab))
    # map 0..1 into ink..warm white per channel (keeps colour, lifts blacks, softens whites)
    x = ink + (white - ink) * np.clip(x, 0, 1)
    return np.clip(x, 0, 1).astype(np.float32)


# ---------------- background model + cutout ----------------
def poly_terms(h, w, deg=3, step=1):
    yy, xx = np.mgrid[0:h:step, 0:w:step].astype(np.float32)
    xx = xx / w * 2 - 1; yy = yy / h * 2 - 1
    terms = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            terms.append((xx ** i) * (yy ** j))
    return np.stack(terms, -1)


def fit_background(img, bgmask, deg=3, iters=3):
    """Fit a smooth polynomial surface per channel to pixels in bgmask. img float 0..1 (H,W,3)."""
    h, w = img.shape[:2]
    s = max(1, int(max(h, w) / 400))
    T = poly_terms(h, w, deg, s)
    sub = img[::s, ::s]
    m = bgmask[::s, ::s].copy()
    for _ in range(iters):
        A = T[m]
        coef = []
        for c in range(3):
            cf, *_ = np.linalg.lstsq(A, sub[..., c][m], rcond=None)
            coef.append(cf)
        pred = np.stack([T @ cf for cf in coef], -1)
        res = np.abs(sub - pred).sum(-1)
        thr = np.percentile(res[m], 90) * 1.5 + 0.01
        m = m & (res < thr)
    Tf = poly_terms(h, w, deg, 1)
    B = np.stack([Tf @ cf for cf in coef], -1)
    return np.clip(B, 0, 1).astype(np.float32)


def box(x, r):
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


def guided_filter(I, p, r=4, eps=1e-3):
    """Grey-guide guided filter (He et al.)."""
    mI = box(I, r); mp = box(p, r)
    cIp = box(I * p, r) - mI * mp
    vI = box(I * I, r) - mI * mI
    a = cIp / (vI + eps); b = mp - a * mI
    return box(a, r) * I + box(b, r)


def guided_filter_color(I, p, r=4, eps=1e-3):
    """Colour-guide guided filter."""
    h, w = p.shape
    mI = [box(I[..., c], r) for c in range(3)]
    mp = box(p, r)
    cov_Ip = [box(I[..., c] * p, r) - mI[c] * mp for c in range(3)]
    var = np.zeros((h, w, 3, 3), np.float32)
    for i in range(3):
        for j in range(i, 3):
            v = box(I[..., i] * I[..., j], r) - mI[i] * mI[j]
            var[..., i, j] = v; var[..., j, i] = v
    var += eps * np.eye(3, dtype=np.float32)
    cov = np.stack(cov_Ip, -1)[..., None]
    a = np.linalg.solve(var, cov)[..., 0]
    b = mp - (a * np.stack(mI, -1)).sum(-1)
    ma = np.stack([box(a[..., c], r) for c in range(3)], -1)
    return (ma * I).sum(-1) + box(b, r)


def push_pull_fill(rgb, w):
    """Fill pixels where weight w~0 with colours propagated from w~1 pixels (multi-scale)."""
    levels_ = []
    c = rgb * w[..., None]; ww = w.copy()
    while min(ww.shape) > 4:
        levels_.append((c, ww))
        c = cv2.resize(c, (max(1, c.shape[1] // 2), max(1, c.shape[0] // 2)), interpolation=cv2.INTER_AREA)
        ww = cv2.resize(ww, (max(1, ww.shape[1] // 2), max(1, ww.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    up = c / np.maximum(ww[..., None], 1e-6)
    for c, ww in reversed(levels_):
        upr = cv2.resize(up, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        cur = c / np.maximum(ww[..., None], 1e-6)
        k = np.clip(ww * 4, 0, 1)[..., None]
        up = cur * k + upr * (1 - k)
    return up


def make_cutout(img, *, bg_seed=None, sure_bg=None, sure_fg=None, thr=None, thr_mul=1.0, deg=3,
                keep="largest", fill_holes=True, holes_keep=None, gc_iter=5, band=6,
                gf_r=3, gf_eps=2e-4, feather=0.6, shrink=0.35, min_area=0.002, debug=None):
    """img: float32 RGB 0..1 at output resolution. Returns (rgb_decontaminated, alpha, bgmodel).
    bg_seed: bool mask of pixels known to be background (default: 4% border band)
    sure_bg/sure_fg: optional bool masks forced in GrabCut."""
    h, w = img.shape[:2]
    if bg_seed is None:
        bg_seed = np.zeros((h, w), bool)
        b = int(0.04 * min(h, w))
        bg_seed[:b] = bg_seed[-b:] = True; bg_seed[:, :b] = bg_seed[:, -b:] = True
    if sure_bg is not None:
        bg_seed = bg_seed | sure_bg
    if sure_fg is not None:
        bg_seed = bg_seed & ~sure_fg
    B = fit_background(img, bg_seed, deg)
    lab_i = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_b = cv2.cvtColor((B * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    D = np.sqrt(((lab_i - lab_b) ** 2 * np.array([0.6, 1.4, 1.4])).sum(-1))
    D = cv2.GaussianBlur(D, (0, 0), 1.0)
    if thr is None:
        d8 = np.clip(D, 0, 255).astype(np.uint8)
        t, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thr = t * thr_mul
    m0 = D > thr
    if sure_bg is not None:
        m0 &= ~sure_bg
    if sure_fg is not None:
        m0 |= sure_fg
    m0 = ndi.binary_opening(m0, iterations=2)
    lab, n = ndi.label(m0)
    if n:
        sizes = ndi.sum(m0, lab, range(1, n + 1))
        if keep == "largest":
            m0 = lab == (np.argmax(sizes) + 1)
        else:
            m0 = np.isin(lab, 1 + np.where(sizes > min_area * h * w)[0])
    if fill_holes:
        m0 = ndi.binary_fill_holes(m0)
    # GrabCut refinement
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    er = ndi.binary_erosion(m0, iterations=band)
    di = ndi.binary_dilation(m0, iterations=band)
    gc[m0] = cv2.GC_PR_FGD
    gc[er] = cv2.GC_FGD
    gc[~di] = cv2.GC_BGD
    if sure_bg is not None:
        gc[sure_bg] = cv2.GC_BGD
    if sure_fg is not None:
        gc[sure_fg] = cv2.GC_FGD
    bgdModel = np.zeros((1, 65), np.float64); fgdModel = np.zeros((1, 65), np.float64)
    u8 = (img * 255).astype(np.uint8)
    cv2.grabCut(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), gc, None, bgdModel, fgdModel, gc_iter, cv2.GC_INIT_WITH_MASK)
    m1 = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m1 = ndi.binary_opening(m1, iterations=1)
    lab, n = ndi.label(m1)
    if n:
        sizes = ndi.sum(m1, lab, range(1, n + 1))
        if keep == "largest":
            m1 = lab == (np.argmax(sizes) + 1)
        else:
            m1 = np.isin(lab, 1 + np.where(sizes > min_area * h * w)[0])
    if fill_holes:
        filled = ndi.binary_fill_holes(m1)
        if holes_keep is not None:
            filled &= ~holes_keep
        m1 = filled
    # smooth jaggies a little
    mf = cv2.GaussianBlur(m1.astype(np.float32), (0, 0), 1.2)
    m1 = mf > 0.5
    # soft alpha via colour guided filter, then crisp it
    a = guided_filter_color(img, m1.astype(np.float32), gf_r, gf_eps)
    a = np.clip(a, 0, 1)
    # keep alpha binary away from the edge band
    near = ndi.binary_dilation(m1, iterations=3) & ~ndi.binary_erosion(m1, iterations=3)
    a = np.where(near, a, m1.astype(np.float32))
    # crisp + slight inward shift (kills residual fringe), then feather
    a = np.clip((a - 0.5 - shrink * 0.25) * 1.6 + 0.5, 0, 1)
    if feather:
        a = cv2.GaussianBlur(a, (0, 0), feather)
    if sure_bg is not None:
        a[sure_bg] = 0
    # colour decontamination
    core = (a > 0.97).astype(np.float32)
    core = cv2.erode(core, np.ones((3, 3), np.uint8), iterations=1)
    fill = push_pull_fill(img, core)
    est = (img - (1 - a[..., None]) * B) / np.maximum(a[..., None], 0.15)
    est = np.clip(est, 0, 1)
    wgt = np.clip((a - 0.25) / 0.7, 0, 1)[..., None]
    edge_col = est * wgt + fill * (1 - wgt)
    # only replace colours in the edge band
    inner = (a > 0.995)[..., None]
    rgb = np.where(inner, img, edge_col * 0.75 + fill * 0.25)
    rgb = np.where(a[..., None] < 0.01, fill, rgb)
    if debug is not None:
        debug.update(dict(D=D, thr=thr, m0=m0, m1=m1, B=B))
    return rgb.astype(np.float32), a.astype(np.float32), B


# ---------------- io ----------------
def load(path, crop=None, maxdim=None, scale=None):
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    if maxdim and max(im.size) > maxdim:
        r = maxdim / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    if scale:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def save_rgba(path, rgb, a, trim=True, pad=6):
    rgb = np.clip(rgb, 0, 1); a = np.clip(a, 0, 1)
    if trim:
        ys, xs = np.where(a > 0.004)
        y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + pad + 1)
        x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + pad + 1)
        rgb = rgb[y0:y1, x0:x1]; a = a[y0:y1, x0:x1]
    a8 = np.round(a * 255).astype(np.uint8)
    rgb8 = np.round(rgb * 255).astype(np.uint8)
    rgb8[a8 == 0] = 0  # better compression
    im = Image.fromarray(np.dstack([rgb8, a8]), "RGBA")
    im.save(path, optimize=True, compress_level=9)
    return im.size


def save_jpg(path, rgb, q=85):
    im = Image.fromarray(np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")
    im.save(path, quality=q, optimize=True, progressive=True, subsampling="4:2:0")
    return im.size


def composite(rgb, a, bg):
    return rgb * a[..., None] + bg[None, None, :] * (1 - a[..., None])


def diff_map(img, B, dw=(0.6, 1.4, 1.4)):
    lab_i = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_b = cv2.cvtColor((np.clip(B, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    D = np.sqrt(((lab_i - lab_b) ** 2 * np.array(dw, np.float32)).sum(-1))
    return cv2.GaussianBlur(D, (0, 0), 1.0), lab_i


def grad_map(lab, sigma=1.0):
    g = cv2.GaussianBlur(lab, (0, 0), sigma)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return np.sqrt((gx ** 2 + gy ** 2).sum(-1))


def keep_components(m, mode="largest", min_frac=0.002):
    lab, n = ndi.label(m)
    if not n:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    if mode == "largest":
        return lab == (np.argmax(sizes) + 1)
    return np.isin(lab, 1 + np.where(sizes > min_frac * m.size)[0])


def finish_alpha(img, m1, B, gf_r=3, gf_eps=2e-4, feather=0.6, shrink=0.35, sure_bg=None, hard=False):
    mf = cv2.GaussianBlur(m1.astype(np.float32), (0, 0), 1.0)
    m1 = mf > 0.5
    if hard:
        a = m1.astype(np.float32)
    else:
        a = np.clip(guided_filter_color(img, m1.astype(np.float32), gf_r, gf_eps), 0, 1)
        near = ndi.binary_dilation(m1, iterations=3) & ~ndi.binary_erosion(m1, iterations=3)
        a = np.where(near, a, m1.astype(np.float32))
        a = np.clip((a - 0.5 - shrink * 0.25) * 1.6 + 0.5, 0, 1)
    if feather:
        a = cv2.GaussianBlur(a, (0, 0), feather)
    if sure_bg is not None:
        a[sure_bg] = 0
    core = (a > 0.97).astype(np.float32)
    core = cv2.erode(core, np.ones((3, 3), np.uint8), iterations=1)
    fill = push_pull_fill(img, core)
    est = np.clip((img - (1 - a[..., None]) * B) / np.maximum(a[..., None], 0.15), 0, 1)
    wgt = np.clip((a - 0.25) / 0.7, 0, 1)[..., None]
    edge_col = est * wgt + fill * (1 - wgt)
    inner = (a > 0.995)[..., None]
    rgb = np.where(inner, img, edge_col * 0.75 + fill * 0.25)
    rgb = np.where(a[..., None] < 0.01, fill, rgb)
    return rgb.astype(np.float32), a.astype(np.float32), m1


def make_cutout_ws(img, *, t_hi=45, t_lo=14, far=45, fg_add=None, bg_add=None, unk_add=None, deg=3, bg_seed=None,
                   keep="largest", fill_holes=True, holes_keep=None, open_it=2, grad_sigma=1.5, fg_erode=2,
                   gc_band=10, gc_iter=4, unk_close=0, smooth_sigma=1.4, dw=(0.6, 1.4, 1.4), D_override=None, final_open=0,
                   gf_r=3, gf_eps=2e-4, feather=0.6, shrink=0.35, debug=None, B=None):
    h, w = img.shape[:2]
    if B is None:
        if bg_seed is None:
            bg_seed = np.zeros((h, w), bool)
            b = int(0.04 * min(h, w))
            bg_seed[:b] = bg_seed[-b:] = True; bg_seed[:, :b] = bg_seed[:, -b:] = True
        if bg_add is not None:
            bg_seed = bg_seed | bg_add
        if fg_add is not None:
            bg_seed = bg_seed & ~fg_add
        B = fit_background(img, bg_seed, deg)
    D, lab = diff_map(img, B, dw)
    if D_override is not None:
        D = D_override
    fg = D > t_hi
    if bg_add is not None:
        fg &= ~bg_add
    fg = ndi.binary_opening(fg, iterations=open_it)
    fg = keep_components(fg, keep)
    if fg_add is not None:
        fg |= fg_add
    if fill_holes:
        fg = ndi.binary_fill_holes(fg)
        if holes_keep is not None:
            fg &= ~holes_keep
    fg = ndi.binary_erosion(fg, iterations=fg_erode)
    if unk_add is not None:
        fg &= ~unk_add
    if fg_add is not None:
        fg |= fg_add
    dist = ndi.distance_transform_edt(~fg)
    bg = (D < t_lo) | (dist > far)
    if bg_add is not None:
        bg |= bg_add
    bg &= ~ndi.binary_dilation(fg, iterations=2)
    if unk_add is not None:
        bg &= ~(unk_add & (D >= t_lo))
        if bg_add is not None:
            bg |= bg_add
    if holes_keep is not None:
        bg |= holes_keep
    markers = np.zeros((h, w), np.int16)
    markers[bg] = 1
    markers[fg] = 2
    G = grad_map(lab, grad_sigma)
    G16 = np.clip(G / max(np.percentile(G, 99.5), 1e-3) * 60000, 0, 65535).astype(np.uint16)
    ws = ndi.watershed_ift(G16, markers)
    m1 = ws == 2
    m1 = keep_components(m1, keep)
    m_ws = m1.copy()
    if gc_band:
        band = ndi.binary_dilation(m1, iterations=gc_band) & ~ndi.binary_erosion(m1, iterations=gc_band)
        gc = np.where(m1, cv2.GC_FGD, cv2.GC_BGD).astype(np.uint8)
        gc[band & m1] = cv2.GC_PR_FGD
        gc[band & ~m1] = cv2.GC_PR_BGD
        gc[fg] = cv2.GC_FGD
        if bg_add is not None:
            gc[bg_add] = cv2.GC_BGD
        if holes_keep is not None:
            gc[holes_keep] = cv2.GC_BGD
        bgdM = np.zeros((1, 65), np.float64); fgdM = np.zeros((1, 65), np.float64)
        u8 = (img * 255).astype(np.uint8)
        cv2.grabCut(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), gc, None, bgdM, fgdM, gc_iter, cv2.GC_INIT_WITH_MASK)
        m1 = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
        m1 = keep_components(m1, keep)
    if unk_close and unk_add is not None:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * unk_close + 1, 2 * unk_close + 1))
        mc = cv2.morphologyEx(m1.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool)
        m1 = np.where(unk_add, mc, m1)
    if final_open:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * final_open + 1, 2 * final_open + 1))
        m1 = cv2.morphologyEx(m1.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
        m1 = keep_components(m1, keep)
    if smooth_sigma:
        m1 = cv2.GaussianBlur(m1.astype(np.float32), (0, 0), smooth_sigma) > 0.5
    if fill_holes:
        f2 = ndi.binary_fill_holes(m1)
        if holes_keep is not None:
            f2 &= ~(holes_keep & ~m1)
        m1 = f2
    rgb, a, m1 = finish_alpha(img, m1, B, gf_r, gf_eps, feather, shrink, bg_add)
    if debug is not None:
        debug.update(dict(D=D, thr=t_hi, m0=fg, bgm=bg, m1=m1, B=B, G=G, unk=unk_add, ws=m_ws))
    return rgb, a, B


def estimate_bg(img, seed, t_hi=40, iters=3, grow=8, smooth=6, deg=3, keep="largest", fg_add=None, bg_add=None):
    """Iterative non-parametric backdrop estimate. Starts with a polynomial fit on `seed`, then
    re-estimates from all pixels outside the (dilated, hole-filled) object via push-pull + blur."""
    B = fit_background(img, seed, deg)
    for _ in range(iters):
        D, _ = diff_map(img, B)
        fg = D > t_hi
        if bg_add is not None:
            fg &= ~bg_add
        fg = keep_components(ndi.binary_opening(fg, iterations=2), keep)
        if fg_add is not None:
            fg |= fg_add
        fg = ndi.binary_fill_holes(fg)
        fg = ndi.binary_dilation(fg, iterations=grow)
        seeds = (~fg).astype(np.float32)
        if bg_add is not None:
            # the manual bg regions (rods, plinths) are not backdrop either: exclude from seeds
            seeds[bg_add] = 0
        Bn = push_pull_fill(img, seeds)
        Bn = cv2.GaussianBlur(Bn, (0, 0), smooth)
        # keep exact pixels where we have backdrop
        B = Bn
    return np.clip(B, 0, 1).astype(np.float32)



def texture_map(img, k=9):
    lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    mu = cv2.blur(L, (k, k)); var = cv2.blur(L * L, (k, k)) - mu * mu
    return np.sqrt(np.clip(var, 0, None))


# ---------------- indexed PNG with smooth alpha edges ----------------
N_OPAQUE = 223  # palette entries 0..222 opaque, 223..254 edge (4 colours x 8 alpha), 255 transparent


def _trim(rgb, a, pad=6):
    ys, xs = np.where(a > 0.004)
    y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + pad + 1)
    return rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]


def _edge_entries(rgb, a, idx, pal):
    """fill entries 223..254 for semi-transparent pixels; returns idx, pal(256x3), alpha table"""
    edge = (a >= 0.01) & (a < 0.985)
    alpha_tab = np.full(256, 255, np.uint8); alpha_tab[255] = 0
    if edge.any():
        cols = rgb[edge].astype(np.float32)
        k = min(4, len(cols))
        if len(cols) >= 8:
            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
            _, lab, cen = cv2.kmeans(cols, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
            lab = lab.ravel()
        else:
            cen = np.repeat(cols.mean(0, keepdims=True), 4, 0); lab = np.zeros(len(cols), int); k = 4
        alev = np.clip(np.floor(a[edge] * 8), 0, 7).astype(int)
        e_idx = N_OPAQUE + lab * 8 + alev
        idx[edge] = e_idx
        for c in range(k):
            for l in range(8):
                j = N_OPAQUE + c * 8 + l
                pal[j] = np.clip(cen[c], 0, 1)
                alpha_tab[j] = int(round((l + 0.5) / 8 * 255))
    idx[a < 0.01] = 255
    pal[255] = 0
    return idx, pal, alpha_tab


def _save_indexed(path, idx, pal, alpha_tab):
    im = Image.fromarray(idx.astype(np.uint8), "P")
    im.putpalette((np.clip(pal, 0, 1) * 255).round().astype(np.uint8).ravel().tolist())
    im.save(path, optimize=True, transparency=bytes(alpha_tab.tolist()))
    return im.size


def save_indexed_natural(path, rgb, a, seed=0):
    rgb, a = _trim(np.clip(rgb, 0, 1), a)
    opaque = a >= 0.985
    # k-means palette in OKLab on opaque pixels
    lab = lin2oklab(srgb2lin(rgb[opaque])).astype(np.float32)
    rng = np.random.default_rng(seed)
    samp = lab[rng.choice(len(lab), min(len(lab), 120000), replace=False)]
    samp = samp * np.array([1.0, 1.6, 1.6], np.float32)  # weight chroma a bit
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-4)
    _, _, cen = cv2.kmeans(samp, N_OPAQUE, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    cen = cen / np.array([1.0, 1.6, 1.6], np.float32)
    pal_rgb = np.clip(lin2srgb(oklab2lin(cen)), 0, 1)
    pal = np.zeros((256, 3), np.float32); pal[:N_OPAQUE] = pal_rgb
    # PIL quantize to the supplied palette with Floyd-Steinberg (C implementation)
    palimg = Image.new("P", (1, 1))
    pl = np.zeros((256, 3), np.uint8); pl[:N_OPAQUE] = (pal_rgb * 255).round()
    pl[N_OPAQUE:] = pl[0]  # unused entries duplicate entry 0 so the quantizer never picks them
    palimg.putpalette(pl.ravel().tolist())
    src = Image.fromarray((rgb * 255).round().astype(np.uint8), "RGB")
    q = np.asarray(src.quantize(palette=palimg, dither=Image.Dither.FLOYDSTEINBERG)).copy()
    q[q >= N_OPAQUE] = 0
    pal[:N_OPAQUE] = pl[:N_OPAQUE] / 255.0
    idx, pal, at = _edge_entries(rgb, a, q.astype(np.int32), pal)
    return _save_indexed(path, idx, pal, at)


def save_indexed_ramp(path, t, a, ramp_fn):
    """duotone stored exactly: t in 0..1 -> 223 ramp entries."""
    rgb_dummy = None
    t, a = _trim(t[..., None], a)
    t = t[..., 0]
    ts = np.linspace(0, 1, N_OPAQUE).astype(np.float32)
    pal = np.zeros((256, 3), np.float32)
    pal[:N_OPAQUE] = ramp_fn(ts[None, :])[0]
    idx = np.clip(np.round(t * (N_OPAQUE - 1)), 0, N_OPAQUE - 1).astype(np.int32)
    # edge entries: 4 t-levels x 8 alpha levels
    alpha_tab = np.full(256, 255, np.uint8); alpha_tab[255] = 0
    edge = (a >= 0.01) & (a < 0.985)
    tl = np.clip(np.floor(t[edge] * 4), 0, 3).astype(int)
    al = np.clip(np.floor(a[edge] * 8), 0, 7).astype(int)
    idx[edge] = N_OPAQUE + tl * 8 + al
    for c in range(4):
        col = ramp_fn(np.array([[(c + 0.5) / 4]], np.float32))[0, 0]
        for l in range(8):
            j = N_OPAQUE + c * 8 + l
            pal[j] = col; alpha_tab[j] = int(round((l + 0.5) / 8 * 255))
    idx[a < 0.01] = 255
    return _save_indexed(path, idx, pal, alpha_tab)


def duotone_t(rgb, alpha=None, gamma=1.0, k=0.25, lo_p=0.8, hi_p=99.6, target=None, gmin=0.6, gmax=2.2):
    L = levels(luminance(rgb), alpha, lo_p, hi_p)
    if target is not None:
        m = (alpha > 0.9) if alpha is not None else np.ones(L.shape, bool)
        med = float(np.clip(np.median(L[m]), 0.05, 0.95))
        gamma = float(np.clip(np.log(target) / np.log(med), gmin, gmax))
    return scurve(L, k, gamma).astype(np.float32)


def make_ramp(dark, light):
    a = lin2oklab(srgb2lin(dark[None, None, :]))
    b = lin2oklab(srgb2lin(light[None, None, :]))
    def ramp(t):
        t = np.asarray(t, np.float32)[..., None]
        return np.clip(lin2srgb(oklab2lin(a + (b - a) * t)), 0, 1).astype(np.float32)
    return ramp
