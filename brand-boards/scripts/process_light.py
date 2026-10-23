"""Movie-grain treatments for the light-mode directions (D, E, F)."""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def load(n, maxedge=1500, trim=False):
    im = Image.open(os.path.join(SRC, f"{n:03d}.jpg")).convert("RGB")
    if trim:  # cut off white scan borders
        a = np.asarray(im).astype(np.float32).mean(-1) / 255
        rows = np.where(a.mean(1) < 0.85)[0]
        cols = np.where(a.mean(0) < 0.85)[0]
        pad = 6
        im = im.crop((cols[0] + pad, rows[0] + pad, cols[-1] - pad, rows[-1] - pad))
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


def mono(a):
    return a[..., 0] * 0.42 + a[..., 1] * 0.46 + a[..., 2] * 0.12


def curve(x, contrast, pivot, black=0.0, white=1.0):
    x = np.clip(x, 0, 1)
    k = 6 * contrast
    s = 1 / (1 + np.exp(-(x - pivot) * k))
    s0, s1 = 1 / (1 + np.exp(pivot * k)), 1 / (1 + np.exp(-(1 - pivot) * k))
    return black + (s - s0) / (s1 - s0) * (white - black)


def blur(a, r):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def noise(h, w, size):
    g = rng.normal(0, 1, (int(h / size) + 2, int(w / size) + 2)).astype(np.float32)
    g = np.asarray(Image.fromarray(g).resize((int(g.shape[1] * size), int(g.shape[0] * size)), Image.BICUBIC))
    return g[:h, :w]


def film_grain(l, fine=0.04, coarse=0.05):
    """Two-scale clumpy grain, strongest in the mid-tones like motion-picture stock."""
    h, w = l.shape[:2]
    g = noise(h, w, 1.0) * fine + noise(h, w, 2.6) * coarse
    m = np.clip(1 - np.abs(l - 0.45) * 1.5, 0.3, 1)
    return g * m


def vignette(h, w, s):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
    return 1 - s * np.clip(d, 0, 1) ** 2


def movie_bw(a, contrast=1.35, pivot=0.42, vig=0.3, halo=0.16, warm=True):
    l = curve(mono(a), contrast, pivot, 0.012, 0.965)
    l = l * vignette(*l.shape, vig)
    bright = np.clip((l - 0.72) / 0.28, 0, 1)
    l = l + blur(bright, 11) * halo
    l = l + film_grain(l)
    if warm:
        lo, hi = hexrgb("#0E0E0D"), hexrgb("#F3F0E8")
        return lo + (hi - lo) * np.clip(l, 0, 1)[..., None]
    return np.clip(l, 0, 1)


def moody_colour(a, vig=0.3):
    l = mono(a)
    c = a * 0.84 + l[..., None] * 0.16                     # mute saturation
    c = np.stack([curve(c[..., i], 1.15, 0.45) for i in range(3)], -1)
    l2 = np.clip(mono(c), 0, 1)
    sh = (1 - l2) ** 2.2
    hi = l2 ** 2.2
    c = c * (1 - 0.32 * sh[..., None]) + hexrgb("#16281F") * 0.32 * sh[..., None]   # green in the shadows
    c = c * (1 - 0.12 * hi[..., None]) + hexrgb("#F4D4CA") * 0.12 * hi[..., None]   # rose cream highlights
    c = c * vignette(*l.shape, vig)[..., None]
    bright = np.clip((l2 - 0.7) / 0.3, 0, 1)
    c = c + blur(bright, 12)[..., None] * np.array([0.24, 0.07, 0.05])              # red halation
    c = c + film_grain(l2, 0.035, 0.04)[..., None]
    return c


def pair(n, name, maxedge=1600, **kw):
    a = load(n, maxedge)
    save(movie_bw(a, **kw), f"{name}_bw.jpg")
    save(moody_colour(a), f"{name}_col.jpg")


# D · Kadrs
pair(167, "d_band", 1800)
pair(301, "d_face", 1400)
save(movie_bw(load(188), 1.3, 0.45), "d_sax_bw.jpg")
save(movie_bw(load(336), 1.3, 0.5), "d_backlit_bw.jpg")
save(movie_bw(load(187), 1.35, 0.42), "d_piano_bw.jpg")

# E · Jaunais vilnis (harder light, deeper blacks)
save(movie_bw(load(346), 1.6, 0.38, 0.2, 0.22), "e_drummer_bw.jpg")
save(movie_bw(load(347), 1.6, 0.38, 0.2, 0.22), "e_hat_bw.jpg")
save(movie_bw(load(313), 1.5, 0.4, 0.2), "e_cymbal_bw.jpg")
pair(295, "e_trumpet", 1600, contrast=1.5, pivot=0.4)
pair(308, "e_trumpet2", 1600, contrast=1.5, pivot=0.4)

# F · Kontaktlapa (contact-sheet frames)
for n, nm, trim in ((321, "f_sax", True), (323, "f_trumpet", True), (325, "f_bass", True),
                    (142, "f_drums", False), (144, "f_sticks", False), (145, "f_smile", False),
                    (333, "f_wine", False), (314, "f_profile", False), (303, "f_keys", False),
                    (240, "f_piano", False), (329, "f_glass", False), (161, "f_guitar", False)):
    save(movie_bw(load(n, 900, trim), 1.3, 0.42, 0.25), f"{nm}_bw.jpg", q=80)
pair(166, "f_desk", 1600)

# textures: dust and scratches (white on transparent) for screen blending
H, W = 1000, 1500
dust = np.zeros((H, W), np.float32)
for _ in range(260):
    y, x = rng.integers(0, H), rng.integers(0, W)
    r = rng.choice([1, 1, 1, 2, 2, 3])
    dust[max(0, y - r):y + r, max(0, x - r):x + r] = rng.uniform(0.4, 1)
for _ in range(30):  # hairs
    y, x = rng.integers(0, H), rng.integers(0, W)
    L = rng.integers(15, 60)
    ang = rng.uniform(0, np.pi)
    for t in range(L):
        yy = int(y + np.sin(ang + t * 0.04) * t)
        xx = int(x + np.cos(ang + t * 0.04) * t)
        if 0 <= yy < H and 0 <= xx < W:
            dust[yy, xx] = 0.8
for _ in range(3):  # vertical scratches
    x = rng.integers(0, W)
    dust[:, x] = np.maximum(dust[:, x], rng.uniform(0.25, 0.5))
dust = blur(dust, 0.7)
Image.fromarray((np.stack([np.ones_like(dust)] * 3 + [np.clip(dust * 1.4, 0, 1)], -1) * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "tex_dust.png"), optimize=True)

print(sorted(os.listdir(OUT)))
