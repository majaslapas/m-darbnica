"""Generate soft out-of-focus 'blurred light' overlay textures for M/darbnica.

All layers are accumulated in linear light on black, tone-mapped with a soft
shoulder (so overlaps roll off toward cream instead of clipping), converted to
sRGB, then given a fine film grain that leaves pure black untouched.

Outputs (screen-blend JPGs on pure black + premultiplied-derived RGBA PNGs):
  light_streaks_v.jpg     1600x1000
  light_bokeh.jpg         1600x1000
  light_mix_portrait.jpg  1000x1400
  light_glow.jpg          1600x1000
"""
import os
import sys
import numpy as np
import cv2
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- colour utils
def hex2lin(h):
    h = h.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


AMBER = hex2lin("#FFB35C")
RED = hex2lin("#C8323A")
CREAM = hex2lin("#FFE2B4")
GOLD = hex2lin("#F2C46B")
ORANGE = hex2lin("#FF8A3D")
ROSE = hex2lin("#E25A5E")
EMBER = hex2lin("#A8242C")
TEAL = hex2lin("#9AD6C4")
ICE = hex2lin("#B4C8EE")
DEEP = hex2lin("#FF9A2E")
STREAK_CORE = AMBER * 0.35 + DEEP * 0.65
YGOLD = hex2lin("#F3BF57")
PGOLD = hex2lin("#F8CD7E")
GREENGOLD = hex2lin("#CFCF74")
SAGE = hex2lin("#A9C9A0")


def blur(img, sigma):
    if sigma <= 0:
        return img
    k = int(sigma * 6) | 1
    return cv2.GaussianBlur(img, (k, k), sigma, borderType=cv2.BORDER_REFLECT)


def smooth_noise_1d(n, sigma, rng):
    v = rng.standard_normal(n + int(sigma * 8)).astype(np.float32)
    k = int(sigma * 6) | 1
    v = cv2.GaussianBlur(v.reshape(1, -1), (k, 1), sigma).ravel()
    v = v[int(sigma * 4):int(sigma * 4) + n]
    return (v - v.mean()) / (v.std() + 1e-6)


def smooth_noise_2d(h, w, sigma, rng):
    v = rng.standard_normal((h, w)).astype(np.float32)
    v = blur(v, sigma)
    return (v - v.mean()) / (v.std() + 1e-6)


def tonemap(lin, exposure=1.0):
    """Soft-shoulder per-channel tone curve: linear in the shadows,
    rolls off smoothly so stacked lights bleach toward cream."""
    x = lin * exposure
    return 1.0 - np.exp(-x)


# ---------------------------------------------------------------- grain
def add_grain(srgb, rng, strength=1.0):
    h, w, _ = srgb.shape
    fine = blur(rng.standard_normal((h, w)).astype(np.float32), 0.55)
    clump = blur(rng.standard_normal((h, w)).astype(np.float32), 1.6)
    g = fine / (fine.std() + 1e-6) * 0.75 + clump / (clump.std() + 1e-6) * 0.45
    chroma = blur(rng.standard_normal((h, w, 3)).astype(np.float32), 1.0)
    chroma /= chroma.std() + 1e-6
    lum = srgb.mean(axis=2, keepdims=True)
    # grain lives only where there is light: pure black stays pure black
    gate = np.clip(lum / 0.06, 0, 1) ** 1.5
    amp = (0.010 * np.sqrt(np.clip(lum, 0, 1)) + 0.0018) * gate * strength
    out = srgb + amp * (g[..., None] + 0.18 * chroma)
    return np.clip(out, 0, 1)


# ---------------------------------------------------------------- streaks
def render_streak(canvas, cx, half_w, rng, *, peak=1.0, soft=0.25, tint=0.5,
                  hot=0.0, edge_hi=0.25, edge_side=1, lean=0.0, wobble=2.0,
                  ymod_sigma=160, ymod_depth=0.45, fade_top=None, fade_bot=None,
                  halo=0.14, striation=0.015):
    """Defocused vertical rod/curtain string seen through a wide aperture.

    Profile across: rounded top-hat (tanh edges), slightly brighter centre,
    a faint highlight running near one edge; tiny vertical striations inside.
    Along y: slow brightness breathing, optional fade at ends, a subtle lean.
    """
    H, W, _ = canvas.shape
    ys = np.arange(H, dtype=np.float32)
    xs = np.arange(W, dtype=np.float32)
    # centre line with subtle lean + slow wobble
    wob = smooth_noise_1d(H, 220, rng) * wobble
    cxy = cx + lean * (ys - H / 2) + wob                       # (H,)
    hw_y = half_w * (1 + 0.05 * smooth_noise_1d(H, 260, rng))  # width breathes a little
    u = (xs[None, :] - cxy[:, None]) / hw_y[:, None]           # (H,W)
    au = np.abs(u)
    body = 0.5 * (1 - np.tanh((au - 1.0) / soft))
    shape = body * (0.62 + 0.38 * np.clip(1 - u * u, 0, 1) ** 0.8)
    # edge highlight (bright rim of a defocused cylinder)
    shape += edge_hi * body * np.exp(-((u - 0.68 * edge_side) / 0.13) ** 2)
    # vertical striations fixed to the rod (move with lean)
    st = smooth_noise_1d(int(W * 3), 4.0 * max(half_w / 40, 1), rng)
    idx = np.clip(((u + 3) / 6 * (W * 3 - 1)).astype(np.int32), 0, W * 3 - 1)
    shape *= 1 + striation * st[idx]
    # along-length breathing
    ym = 1 - ymod_depth * (0.5 + 0.5 * np.tanh(smooth_noise_1d(H, ymod_sigma, rng)))
    if fade_top is not None:
        a, b = fade_top
        ym *= np.clip((ys - a * H) / max((b - a) * H, 1), 0, 1) ** 1.3
    if fade_bot is not None:
        a, b = fade_bot
        ym *= np.clip((b * H - ys) / max((b - a) * H, 1), 0, 1) ** 1.3
    shape *= ym[:, None]
    shape = np.clip(shape, 0, None)

    # colour across the streak: red edges -> amber core (-> cream if hot)
    t = np.clip(body, 0, 1) ** 1.6
    edge_col = RED * (1 - tint) + ORANGE * tint * 0.6 + AMBER * tint * 0.4
    col = edge_col[None, None, :] * (1 - t[..., None]) + STREAK_CORE[None, None, :] * t[..., None]
    if hot > 0:
        col = col * (1 - hot * t[..., None] ** 2) + CREAM * hot * t[..., None] ** 2
    layer = shape[..., None] * col * peak
    canvas += layer
    # bloom / halo – light scattering around the bright rod
    if halo > 0:
        hb = blur(shape, half_w * 1.4)[..., None]
        canvas += hb * (RED * 0.6 + DEEP * 0.4) * peak * halo
        hb2 = blur(shape, half_w * 3.0)[..., None]
        canvas += hb2 * EMBER * peak * halo * 0.25


# ---------------------------------------------------------------- bokeh
def render_disc(canvas, x, y, r, col, rng, *, inten=1.0, rim=0.0, soft=0.07,
                centre_bias=0.0, cat_eye=0.0, ca=0.012, texture=0.04, rot=None):
    H, W, _ = canvas.shape
    pad = int(r * 1.35 + 6)
    x0, x1 = int(max(0, x - pad)), int(min(W, x + pad))
    y0, y1 = int(max(0, y - pad)), int(min(H, y + pad))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - x, yy - y
    # mechanical vignetting -> cat's-eye: intersect with an offset circle
    if rot is None:
        cx_, cy_ = W / 2, H / 2
        vx, vy = x - cx_, y - cy_
        n = np.hypot(vx, vy) + 1e-6
        vx, vy = vx / n, vy / n
    else:
        vx, vy = np.cos(rot), np.sin(rot)
    off = cat_eye * r
    if texture > 0:
        nz = blur(rng.standard_normal(dx.shape).astype(np.float32), max(r / 9, 1.0))
        tex = 1 + texture * nz / (nz.std() + 1e-6)
    else:
        tex = 1.0
    for ch, scale in enumerate((1 + ca, 1.0, 1 - ca)):
        rr = r * scale
        d = np.hypot(dx, dy) / rr
        d2 = np.hypot(dx + vx * off, dy + vy * off) / rr
        s = soft
        m = 0.5 * (1 - np.tanh((d - 1) / s)) * 0.5 * (1 - np.tanh((d2 - 1) / s))
        prof = 1 - centre_bias * np.clip(d, 0, 1) ** 2 + (centre_bias < 0) * 0
        prof = np.clip(prof, 0.0, None)
        ring = rim * np.exp(-((np.minimum(d, d2) - 0.9) / 0.075) ** 2)
        onion = 1 + 0.035 * np.sin(d * 23.0 + 1.3)
        val = m * (prof + ring) * onion * tex
        canvas[y0:y1, x0:x1, ch] += val * col[ch] * inten


def scatter_cluster(rng, n, cx, cy, sx, sy, W, H):
    pts = []
    while len(pts) < n:
        x = rng.normal(cx * W, sx * W)
        y = rng.normal(cy * H, sy * H)
        if -0.05 * W < x < 1.05 * W and -0.05 * H < y < 1.05 * H:
            pts.append((x, y))
    return pts


WARM_POOL = [(YGOLD, 5), (PGOLD, 4), (GOLD, 3), (AMBER, 3), (ORANGE, 1.2), (CREAM, 0.8), (ROSE, 0.4)]
COOL_POOL = [(GREENGOLD, 2), (SAGE, 1.2), (TEAL * 0.5 + PGOLD * 0.5, 0.6)]


def pick_colour(rng, cool_p=0.0):
    if rng.random() < cool_p:
        pool = COOL_POOL
    else:
        pool = WARM_POOL
    w = np.array([p[1] for p in pool], float)
    c = pool[rng.choice(len(pool), p=w / w.sum())][0]
    # jitter hue slightly
    j = 1 + rng.normal(0, 0.05, 3).astype(np.float32)
    return np.clip(c * j, 0, 1)


def bokeh_field(H, W, rng, clusters, *, mask=None, cool_p=0.06, gain=1.0,
                n_bg=60):
    """clusters: list of (cx, cy, sx, sy, n_large, n_mid, n_small)"""
    fg = np.zeros((H, W, 3), np.float32)
    mid = np.zeros((H, W, 3), np.float32)
    bg = np.zeros((H, W, 3), np.float32)
    S = min(W, H)
    diag = np.hypot(W / 2, H / 2)

    def place(layer, pts, rmin, rmax, base, rim_p, soft_rng, centre_rng):
        for (x, y) in pts:
            if mask is not None:
                xi, yi = int(np.clip(x, 0, W - 1)), int(np.clip(y, 0, H - 1))
                if rng.random() > mask[yi, xi]:
                    continue
            r = np.exp(rng.uniform(np.log(rmin), np.log(rmax))) * S
            col = pick_colour(rng, cool_p)
            # energy spreads over a larger circle -> bigger = fainter
            inten = base * rng.uniform(0.45, 1.15) * (0.06 * S / r) ** 0.55
            rim = rng.uniform(0.25, 0.6) if rng.random() < rim_p else rng.uniform(0, 0.08)
            centre = rng.uniform(*centre_rng)
            dist = np.hypot(x - W / 2, y - H / 2) / diag
            cat = 0.55 * max(0.0, dist - 0.35) ** 1.2
            render_disc(layer, x, y, r, col, rng, inten=inten, rim=rim,
                        soft=rng.uniform(*soft_rng), centre_bias=centre,
                        cat_eye=cat, ca=rng.uniform(0.006, 0.018),
                        texture=rng.uniform(0.008, 0.02))

    for (cx, cy, sx, sy, nl, nm, ns) in clusters:
        place(fg, scatter_cluster(rng, nl, cx, cy, sx * 1.2, sy * 1.2, W, H),
              0.05, 0.095, 0.13 * gain, 0.30, (0.12, 0.24), (0.0, 0.30))
        place(mid, scatter_cluster(rng, nm, cx, cy, sx, sy, W, H),
              0.024, 0.05, 0.19 * gain, 0.45, (0.08, 0.14), (-0.05, 0.20))
        place(bg, scatter_cluster(rng, ns, cx, cy, sx * 0.8, sy * 0.8, W, H),
              0.012, 0.024, 0.22 * gain, 0.25, (0.12, 0.20), (0.0, 0.2))
    # sparse faint far-background specks everywhere
    pts = [(rng.uniform(0, W), rng.uniform(0, H)) for _ in range(n_bg)]
    place(bg, pts, 0.008, 0.016, 0.10 * gain, 0.1, (0.16, 0.24), (0.0, 0.3))
    # depth: background discs a bit softer, foreground gets a tiny bloom
    out = blur(bg, 2.2) + blur(mid, 1.0) + fg
    out += blur(fg + mid, 0.04 * S) * 0.10
    return out


# ---------------------------------------------------------------- glow
def corner_glow(H, W, rng, corner=(0.0, 0.0), *, gain=1.0, stretch=(1.25, 0.85),
                angle=0.55):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    S = max(W, H)
    cx, cy = corner[0] * W, corner[1] * H
    # push source just outside the frame
    cx += (-0.06 if corner[0] < 0.5 else 0.06) * W
    cy += (-0.10 if corner[1] < 0.5 else 0.10) * H
    dx, dy = (xx - cx) / S, (yy - cy) / S
    ca, sa = np.cos(angle), np.sin(angle)
    if corner[0] > 0.5:
        sa = -sa
    if corner[1] > 0.5:
        sa = -sa
    u = (dx * ca + dy * sa) / stretch[0]
    v = (-dx * sa + dy * ca) / stretch[1]
    d = np.sqrt(u * u + v * v)
    # warp distance with low-frequency haze so falloff isn't a perfect gradient
    warp = smooth_noise_2d(H, W, 0.09 * S, rng) * 0.05 + smooth_noise_2d(H, W, 0.03 * S, rng) * 0.012
    d = np.clip(d + warp, 0, None)
    # hot source (Lorentzian-ish scatter) + exponential haze tails that
    # actually reach black, so the far side of the frame stays dark
    core = 1.0 / (1 + (d / 0.10) ** 2) ** 2.0
    midg = np.exp(-(d / 0.26) ** 1.6)
    outer = np.exp(-(d / 0.50) ** 2.0)
    haze = 1 + 0.12 * smooth_noise_2d(H, W, 0.05 * S, rng)
    lin = (core[..., None] * (CREAM * 0.45 + AMBER * 0.55) * 1.5
           + midg[..., None] * (DEEP * 0.45 + ORANGE * 0.25 + RED * 0.30) * 0.38
           + outer[..., None] * (RED * 0.8 + EMBER * 0.2) * 0.07)
    lin *= haze[..., None] * gain
    # gentle broad veils that drift away from the source (scatter in haze)
    veil_dir = np.arctan2(dy, dx)
    veil = 0.5 + 0.5 * np.sin(veil_dir * 9 + 0.7 * smooth_noise_2d(H, W, 0.08 * S, rng))
    veil = blur(veil.astype(np.float32), 0.02 * S)
    lin *= (0.88 + 0.12 * veil)[..., None]
    return lin


# ---------------------------------------------------------------- outputs
def finish(lin, name, rng, exposure=1.0, grain=1.0):
    tm = tonemap(lin, exposure)
    srgb = lin2srgb(tm).astype(np.float32)
    srgb = add_grain(srgb, rng, grain)
    u8 = (srgb * 255 + 0.5).astype(np.uint8)
    # pure black floor: kill tiny tonemap residue in empty areas
    Image.fromarray(u8).save(os.path.join(OUT, name + ".jpg"), quality=92,
                             subsampling=0, optimize=True)
    # alpha version: alpha = max channel, colour = unpremultiplied
    a = srgb.max(axis=2)
    rgb = np.where(a[..., None] > 1e-4, srgb / np.maximum(a[..., None], 1e-4), 0)
    rgba = np.dstack([rgb, a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(
        os.path.join(OUT, name + "_alpha.png"), optimize=True)
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(
        os.path.join(OUT, name + "_alpha.webp"), quality=88, method=6)
    print("wrote", name, u8.shape, "max", u8.max(), "mean", round(u8.mean(), 1))


def make_streaks(rng):
    H, W = 1000, 1600
    c = np.zeros((H, W, 3), np.float32)
    S = W
    specs = [
        # cx,   half_w, peak, soft, tint, hot, edge_hi, side, lean,   extras
        (0.050, 0.030, 0.95, 0.30, 0.35, 0.10, 0.30, 1, 0.0035, dict()),
        (0.088, 0.011, 0.45, 0.25, 0.50, 0.00, 0.10, 1, 0.0033, dict(halo=0.05, ymod_depth=0.6)),
        (0.212, 0.016, 0.45, 0.24, 0.60, 0.00, 0.20, -1, -0.002, dict(fade_top=(0.0, 0.35))),
        (0.285, 0.033, 0.66, 0.32, 0.50, 0.00, 0.18, 1, 0.0015, dict(ymod_depth=0.55)),
        (0.318, 0.010, 0.36, 0.25, 0.40, 0.00, 0.10, -1, 0.0017, dict(halo=0.05, fade_bot=(0.6, 1.0))),
        (0.605, 0.012, 0.28, 0.22, 0.30, 0.00, 0.25, 1, 0.004, dict(fade_bot=(0.55, 1.0))),
        (0.795, 0.018, 0.50, 0.26, 0.45, 0.00, 0.15, 1, -0.0022, dict(halo=0.08, ymod_depth=0.6)),
        (0.835, 0.032, 1.00, 0.28, 0.55, 0.12, 0.28, -1, -0.0025, dict()),
        (0.955, 0.024, 0.55, 0.40, 0.20, 0.00, 0.15, 1, 0.001, dict(ymod_depth=0.6)),
    ]
    for cx, hw, pk, soft, tint, hot, eh, side, lean, ex in specs:
        render_streak(c, cx * W, hw * S, rng, peak=pk * 0.62, soft=soft, tint=tint,
                      hot=hot, edge_hi=eh, edge_side=side, lean=lean, **ex)
    # faint warm atmosphere tying the streaks together
    fog = (0.5 + 0.5 * smooth_noise_2d(H, W, 180, rng)) ** 2
    c += fog[..., None] * EMBER * 0.004
    finish(c, "light_streaks_v", rng, exposure=1.0)
    return c


def make_bokeh(rng):
    H, W = 1000, 1600
    clusters = [
        (0.16, 0.32, 0.09, 0.16, 3, 5, 4),
        (0.30, 0.80, 0.07, 0.09, 1, 2, 3),
        (0.74, 0.62, 0.10, 0.14, 4, 6, 5),
        (0.92, 0.18, 0.05, 0.10, 1, 3, 2),
        (0.52, 0.08, 0.10, 0.05, 1, 1, 2),
    ]
    c = bokeh_field(H, W, rng, clusters, cool_p=0.07, gain=1.0, n_bg=12)
    fog = (0.5 + 0.5 * smooth_noise_2d(H, W, 200, rng)) ** 2
    c += fog[..., None] * EMBER * 0.003
    finish(c, "light_bokeh", rng, exposure=1.0)


def make_mix_portrait(rng):
    H, W = 1400, 1000
    c = np.zeros((H, W, 3), np.float32)
    S = W
    specs = [
        (0.040, 0.044, 0.90, 0.32, 0.35, 0.10, 0.30, 1, 0.0025, dict()),
        (0.098, 0.014, 0.42, 0.25, 0.50, 0.00, 0.10, 1, 0.0024, dict(halo=0.05, ymod_depth=0.6)),
        (0.180, 0.022, 0.48, 0.24, 0.55, 0.00, 0.22, -1, -0.002, dict(fade_bot=(0.6, 1.0))),
        (0.640, 0.012, 0.16, 0.22, 0.40, 0.00, 0.20, 1, 0.003, dict(fade_top=(0.1, 0.55), fade_bot=(0.75, 1.0))),
        (0.800, 0.026, 0.62, 0.28, 0.55, 0.00, 0.25, -1, -0.002, dict()),
        (0.835, 0.012, 0.35, 0.24, 0.45, 0.00, 0.10, 1, -0.0021, dict(halo=0.05, fade_top=(0.0, 0.4))),
        (0.948, 0.042, 0.85, 0.36, 0.30, 0.08, 0.20, 1, 0.0015, dict(ymod_depth=0.5)),
    ]
    for cx, hw, pk, soft, tint, hot, eh, side, lean, ex in specs:
        render_streak(c, cx * W, hw * S, rng, peak=pk * 0.60, soft=soft, tint=tint,
                      hot=hot, edge_hi=eh, edge_side=side, lean=lean, **ex)
    # bokeh mostly along edges / corners, centre calmer
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    e = np.sqrt(((xx / W - 0.5) / 0.30) ** 2 + ((yy / H - 0.50) / 0.36) ** 2)
    mask = np.clip((e - 0.55) / 0.6, 0.06, 1.0)
    clusters = [
        (0.10, 0.18, 0.08, 0.08, 2, 3, 3),
        (0.90, 0.42, 0.07, 0.12, 2, 4, 3),
        (0.14, 0.72, 0.08, 0.10, 2, 3, 3),
        (0.80, 0.90, 0.12, 0.05, 2, 3, 3),
        (0.55, 0.04, 0.12, 0.03, 1, 1, 2),
    ]
    c += bokeh_field(H, W, rng, clusters, mask=mask, cool_p=0.07, gain=0.9, n_bg=8)
    # faint glow from the lower-left, tying it together
    c += corner_glow(H, W, rng, corner=(0.0, 1.0), gain=0.30)
    finish(c, "light_mix_portrait", rng, exposure=1.0)


def make_glow(rng):
    H, W = 1000, 1600
    c = corner_glow(H, W, rng, corner=(0.0, 0.0), gain=1.0)
    finish(c, "light_glow", rng, exposure=1.0)


if __name__ == "__main__":
    make_streaks(np.random.default_rng(11))
    make_bokeh(np.random.default_rng(23))
    make_mix_portrait(np.random.default_rng(37))
    make_glow(np.random.default_rng(41))
