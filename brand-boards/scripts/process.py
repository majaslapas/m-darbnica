"""Photo treatments + textures for the M/darbnica brand boards."""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

SRC = sys.argv[1]   # folder with candidate photos (NNN.jpg)
OUT = sys.argv[2]   # output folder
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def load(n, maxedge=1500):
    im = Image.open(os.path.join(SRC, f"{n:03d}.jpg")).convert("RGB")
    im.thumbnail((maxedge, maxedge), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def save(a, name, q=82):
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, name), quality=q, optimize=True, progressive=True)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def mono(a, mix=(0.36, 0.50, 0.14)):
    return a[..., 0] * mix[0] + a[..., 1] * mix[1] + a[..., 2] * mix[2]


def curve(l, contrast=1.25, pivot=0.45, black=0.0, white=1.0):
    # smooth S-curve around pivot
    x = np.clip(l, 0, 1)
    s = 1 / (1 + np.exp(-(x - pivot) * 6 * contrast))
    s0 = 1 / (1 + np.exp(pivot * 6 * contrast))
    s1 = 1 / (1 + np.exp(-(1 - pivot) * 6 * contrast))
    s = (s - s0) / (s1 - s0)
    return black + s * (white - black)


def grain(shape, amount=0.06, size=1.0):
    h, w = shape[:2]
    g = rng.normal(0, 1, (int(h / size) + 1, int(w / size) + 1)).astype(np.float32)
    if size != 1.0:
        g = np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC))
    return g[:h, :w] * amount


def add_grain(l, amount=0.06, size=1.3):
    # stronger in midtones, like silver halide
    m = 1 - np.abs(l - 0.5) * 1.4
    return l + grain(l.shape, amount, size) * np.clip(m, 0.25, 1)


def vignette(l, strength=0.35):
    h, w = l.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
    v = 1 - strength * np.clip(d, 0, 1) ** 2
    return l * (v if l.ndim == 2 else v[..., None])


def blur(a, r):
    if a.ndim == 2:
        im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
        return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def bw(a, contrast=1.25, pivot=0.45, g=0.055, vig=0.3, black=0.02, white=0.97):
    l = curve(mono(a), contrast, pivot, black, white)
    l = vignette(l, vig)
    return add_grain(l, g)


def tone(l, shadow, high, mid=None):
    s, hgh = hexrgb(shadow), hexrgb(high)
    l = np.clip(l, 0, 1)[..., None]
    if mid is None:
        return s + (hgh - s) * l
    m = hexrgb(mid)
    lo = s + (m - s) * np.clip(l * 2, 0, 1)
    hi = m + (hgh - m) * np.clip(l * 2 - 1, 0, 1)
    return np.where(l < 0.5, lo, hi)


def rgb2hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0)
    return h, s, mx


def selective(a, hue_lo, hue_hi, smin=0.35, vmin=0.12, feather=3, desat=0.85, shift_to=None, out_bw=None, ymin=0.0):
    h, s, v = rgb2hsv(a)
    if hue_lo > hue_hi:
        hm = (h >= hue_lo) | (h <= hue_hi)
    else:
        hm = (h >= hue_lo) & (h <= hue_hi)
    m = (hm & (s > smin) & (v > vmin)).astype(np.float32)
    if ymin > 0:
        yy = np.linspace(0, 1, m.shape[0])[:, None]
        m = m * np.clip((yy - ymin) / 0.06, 0, 1)
    m = blur(m, feather)
    m = np.clip(m * 1.4, 0, 1)
    col = a.copy()
    if shift_to is not None:
        # recolour kept areas toward a brand colour, keeping their luminance
        t = hexrgb(shift_to)
        lum = mono(a)[..., None]
        tl = (t * np.array([0.36, 0.5, 0.14])).sum()
        col = np.clip(t * (lum / max(tl, 1e-3)) * 0.9, 0, 1) * 0.75 + a * 0.25
    col = col * desat + mono(col)[..., None] * (1 - desat)
    base = out_bw if out_bw is not None else bw(a)
    base3 = np.stack([base] * 3, -1)
    return base3 * (1 - m[..., None]) + col * m[..., None]


# ---------------------------------------------------------------- A · Plate
# record-sleeve duotones
l = curve(mono(load(186)), 1.35, 0.5, 0, 1)
save(tone(add_grain(l, 0.05), "#131211", "#EFB9B4"), "a_sax_pink.jpg")
l = curve(mono(load(191)), 1.3, 0.45, 0, 1)
save(tone(add_grain(l, 0.05), "#0E1A14", "#E9E3D7", "#3E6150"), "a_bass_green.jpg")
save(bw(load(184), 1.35, 0.48, 0.06, 0.25), "a_drums_bw.jpg")
save(bw(load(143), 1.2, 0.4, 0.06, 0.2), "a_trumpet_bw.jpg")
a = load(178)
save(selective(a, 340, 14, smin=0.4, shift_to="#CF5C63", out_bw=bw(a, 1.2, 0.35, 0.05, 0.2)), "a_turntable_sel.jpg")
l = curve(mono(load(77)), 1.35, 0.45, 0, 1)
save(tone(add_grain(l, 0.05), "#131211", "#CF5C63", "#5A2328"), "a_sax2_rouge.jpg")

# ---------------------------------------------------------------- B · Kino
a = load(366)
save(selective(a, 342, 16, smin=0.45, desat=0.8, shift_to="#B8414E", out_bw=bw(a, 1.3, 0.38, 0.07, 0.45), ymin=0.6), "b_seats_sel.jpg")
save(bw(load(106), 1.45, 0.42, 0.075, 0.5, 0.01, 0.95), "b_hat_bw.jpg")
save(bw(load(185), 1.4, 0.42, 0.075, 0.45, 0.01, 0.95), "b_spot_bw.jpg")
save(bw(load(103), 1.3, 0.35, 0.075, 0.4, 0.01, 0.95), "b_profile_bw.jpg")
save(bw(load(389), 1.2, 0.4, 0.075, 0.45), "b_audience_bw.jpg")
a = load(179)
save(np.clip(a * 1.05, 0, 1), "b_smoke_red.jpg")

# ---------------------------------------------------------------- C · Partitūra (warm fibre prints)
def warm(n, contrast=1.15, pivot=0.45, g=0.045, vig=0.18):
    l = curve(mono(load(n)), contrast, pivot, 0.0, 1.0)
    l = vignette(l, vig)
    l = add_grain(l, g)
    return tone(l, "#1C1B19", "#F1EADD", "#8C877E")

save(warm(374), "c_dance.jpg")
save(warm(375, 1.1), "c_gallery.jpg")
save(warm(141, 1.15, 0.5), "c_laugh.jpg")
save(warm(363, 1.1, 0.5), "c_facade.jpg")
save(warm(285, 1.15, 0.45), "c_friends.jpg")
save(warm(352, 1.2, 0.4), "c_keys.jpg")
save(warm(371, 1.15, 0.45), "c_courtyard.jpg")

# ---------------------------------------------------------------- reveal pairs (B&W -> colour)
for n, nm in ((77, "sax"), (355, "bass"), (32, "singer")):
    a = load(n, 1600)
    save(bw(a, 1.3, 0.42, 0.05, 0.3), f"r_{nm}_bw.jpg")
    c = a * 0.92 + mono(a)[..., None] * 0.08          # slightly muted, filmic colour
    c = vignette(c, 0.25)
    c = c + grain(c.shape, 0.035, 1.3)[..., None]
    save(c, f"r_{nm}_col.jpg")

# cover
save(bw(load(384), 1.25, 0.38, 0.065, 0.45), "cover_house.jpg")

# ---------------------------------------------------------------- textures
def fbm(h, w, octaves=6, base=4, seed=1):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = r.random((n + 1, int(n * w / h) + 2)).astype(np.float32)
        g = np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC))
        out += g * amp
        tot += amp
        amp *= 0.5
    return out / tot


def rgba(a, alpha, name):
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    im = np.concatenate([a, np.clip(alpha, 0, 1)[..., None]], -1)
    Image.fromarray((im * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(OUT, name), optimize=True)


# film grain tile (neutral grey, used with overlay blend)
g = rng.normal(0.5, 0.16, (400, 400)).astype(np.float32)
g = 0.55 * g + 0.45 * blur(g, 0.6)
save(np.clip(g, 0, 1), "tex_grain.jpg", q=90)

# smoke: domain-warped fbm, white with alpha
H, W = 900, 1600
f1 = fbm(H, W, 6, 3, 11)
f2 = fbm(H, W, 6, 3, 12)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
wx = np.clip(xx + (f1 - 0.5) * 520, 0, W - 1).astype(int)
wy = np.clip(yy + (f2 - 0.5) * 320, 0, H - 1).astype(int)
f3 = fbm(H, W, 7, 2, 13)[wy, wx]
sm = np.clip((f3 - 0.45) * 2.6, 0, 1) ** 1.6
sm = blur(sm, 6) * 0.9 + blur(sm, 1.5) * 0.1
sm *= np.clip(1 - np.abs(yy - H * 0.55) / (H * 0.6), 0, 1)
rgba(np.ones_like(sm), sm * 0.85, "tex_smoke.png")

# projector beam: cone from the top-right corner, with dust and smoke inside
H, W = 1000, 1600
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
ox, oy = W * 0.98, H * 0.06
ang = np.arctan2(yy - oy, xx - ox)
centre = np.arctan2(H * 0.7 - oy, W * 0.1 - ox)
spread = 0.30
cone = np.clip(1 - np.abs(ang - centre) / spread, 0, 1) ** 1.15
dist = np.sqrt((xx - ox) ** 2 + (yy - oy) ** 2) / W
cone *= np.clip(dist * 3, 0, 1) * np.exp(-dist * 0.9)
haze = fbm(H, W, 6, 3, 21)
cone *= 0.35 + 1.0 * haze ** 1.3
dust = (rng.random((H, W)) > 0.9993).astype(np.float32)
dust = blur(dust, 0.8) * 9
beam = np.clip(cone * 0.9 + dust * cone * 2.5, 0, 1)
rgba(np.stack([np.ones_like(beam), np.ones_like(beam) * 0.97, np.ones_like(beam) * 0.9], -1), beam, "tex_beam.png")

# paper fibre (warm newsprint)
H, W = 900, 900
p = fbm(H, W, 6, 8, 31) * 0.5 + rng.normal(0, 1, (H, W)).astype(np.float32) * 0.02
fib = blur((rng.random((H, W)) > 0.996).astype(np.float32), 0.7)
p = 0.5 + (p - 0.5) * 0.16 - fib * 0.25
paper = tone(np.clip(p, 0, 1), "#D9D1C2", "#F3EDE2")
save(paper, "tex_paper.jpg", q=88)

# light refraction streak (for B)
H, W = 700, 1400
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
band = np.exp(-((yy - H * 0.5 - (xx - W * 0.5) * 0.35) / (H * 0.09)) ** 2)
band *= np.exp(-((xx - W * 0.55) / (W * 0.33)) ** 2)
r = np.exp(-((yy - H * 0.47 - (xx - W * 0.5) * 0.35) / (H * 0.05)) ** 2)
gch = np.exp(-((yy - H * 0.53 - (xx - W * 0.5) * 0.35) / (H * 0.05)) ** 2)
col = np.stack([0.95 * r + 0.75 * band, 0.55 * band + 0.6 * gch, 0.5 * band + 0.45 * gch], -1)
alpha = np.clip(band * 0.8 + 0.4 * (r + gch) * band, 0, 1)
rgba(np.clip(col / np.maximum(col.max(-1, keepdims=True), 1e-3), 0, 1), blur(alpha, 4), "tex_prism.png")

print("done", sorted(os.listdir(OUT)))
