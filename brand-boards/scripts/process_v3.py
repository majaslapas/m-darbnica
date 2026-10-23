"""Round-3 assets: A hero, grain layer, C paper stocks, E party photos and poster wall."""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(23)


def load(n, maxedge=1600):
    im = Image.open(os.path.join(SRC, f"{n:03d}.jpg")).convert("RGB")
    im.thumbnail((maxedge, maxedge), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def save(a, name, q=84):
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, name), quality=q, optimize=True, progressive=True)


def save_rgba(rgb, alpha, name):
    rgb = np.clip(rgb, 0, 1)
    if rgb.ndim == 2:
        rgb = np.stack([rgb] * 3, -1)
    im = np.concatenate([rgb, np.clip(alpha, 0, 1)[..., None]], -1)
    Image.fromarray((im * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(OUT, name), optimize=True)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def mono(a):
    return a[..., 0] * 0.4 + a[..., 1] * 0.47 + a[..., 2] * 0.13


def curve(x, contrast, pivot, black=0.0, white=1.0):
    x = np.clip(x, 0, 1)
    k = 6 * contrast
    s = 1 / (1 + np.exp(-(x - pivot) * k))
    s0, s1 = 1 / (1 + np.exp(pivot * k)), 1 / (1 + np.exp(-(1 - pivot) * k))
    return black + (s - s0) / (s1 - s0) * (white - black)


def blur(a, r):
    if a.ndim == 3:
        return np.stack([blur(a[..., i], r) for i in range(a.shape[2])], -1)
    scale = max(float(np.abs(a).max()), 1e-6)
    im = Image.fromarray((np.clip(a / scale, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255 * scale


def noise(h, w, size):
    g = rng.normal(0, 1, (int(h / size) + 2, int(w / size) + 2)).astype(np.float32)
    g = np.asarray(Image.fromarray(g, mode="F").resize((int(g.shape[1] * size), int(g.shape[0] * size)), Image.BICUBIC))
    return g[:h, :w]


def film_grain(l, fine=0.035, coarse=0.04):
    h, w = l.shape[:2]
    g = noise(h, w, 1.0) * fine + noise(h, w, 2.4) * coarse
    return g * np.clip(1 - np.abs(l - 0.45) * 1.5, 0.3, 1)


def vignette(h, w, s):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
    return 1 - s * np.clip(d, 0, 1) ** 2


def periodic_noise(n, beta=2.0, seed=1):
    """Seamless 1/f^beta noise on an n x n torus, normalised to 0..1."""
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / f ** (beta / 2)
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    out = (out - out.min()) / (out.max() - out.min())
    return out.astype(np.float32)


def periodic_fibres(n, count, length, seed, width=0.8):
    """Short curved fibres drawn on a torus so the tile stays seamless."""
    r = np.random.default_rng(seed)
    img = np.zeros((n, n), np.float32)
    for _ in range(count):
        x, y = r.uniform(0, n), r.uniform(0, n)
        ang = r.uniform(0, np.pi)
        bend = r.uniform(-0.04, 0.04)
        L = int(r.uniform(length * 0.4, length))
        v = r.uniform(0.4, 1)
        for t in range(L):
            a = ang + bend * t
            x += np.cos(a)
            y += np.sin(a)
            img[int(y) % n, int(x) % n] = max(img[int(y) % n, int(x) % n], v)
    tiled = np.tile(img, (3, 3))
    tiled = blur(tiled, width)
    return tiled[n:2 * n, n:2 * n]


# ---------------------------------------------------------------- A · hero (clear, warm, moody)
a = load(32, 1600)
l = curve(mono(a), 1.15, 0.45, 0.0, 1.0)
l = l * vignette(*l.shape, 0.18)
sh, mid, hi = hexrgb("#2A211F"), hexrgb("#9A5258"), hexrgb("#F6D9D2")
t = np.clip(l, 0, 1)[..., None]
duo = np.where(t < 0.5, sh + (mid - sh) * (t * 2), mid + (hi - mid) * (t * 2 - 1))
duo = duo + film_grain(l, 0.03, 0.035)[..., None]
save(duo, "a_hero_duo.jpg")
c = a * 0.9 + mono(a)[..., None] * 0.1
c = np.stack([curve(c[..., i], 1.05, 0.42, 0.04, 1.0) for i in range(3)], -1)    # lift the shadows a little
c = c * vignette(*l.shape, 0.18)[..., None]
c = c + film_grain(mono(c), 0.03, 0.035)[..., None]
save(c, "a_hero_col.jpg")

# ---------------------------------------------------------------- grain layer for whole boards (normal blend)
n = 320
g1 = rng.normal(0, 1, (n, n)).astype(np.float32)
g2 = np.tile(rng.normal(0, 1, (n // 2, n // 2)).astype(np.float32), (1, 1))
g2 = np.asarray(Image.fromarray(g2, mode="F").resize((n, n), Image.BICUBIC))
g = g1 * 0.6 + g2 * 0.8
g = g / np.abs(g).max()
white = (g > 0).astype(np.float32)
alpha = np.clip(np.abs(g) ** 1.4 * 0.55, 0, 0.55)
save_rgba(white, alpha, "tex_grain_layer.png")

# ---------------------------------------------------------------- C · paper stocks (seamless tiles)
N = 640
mott = periodic_noise(N, 2.2, 5) * 0.7 + periodic_noise(N, 1.2, 6) * 0.3
fib_d = periodic_fibres(N, 900, 26, 7)
fib_l = periodic_fibres(N, 500, 22, 8)
speck = (np.random.default_rng(9).random((N, N)) > 0.9993).astype(np.float32)
speck = blur(np.tile(speck, (3, 3)), 0.8)[N:2 * N, N:2 * N] * 3
base = hexrgb("#EFE9DD")
cot = base + (mott[..., None] - 0.5) * 0.045 - fib_d[..., None] * 0.07 + fib_l[..., None] * 0.05 - speck[..., None] * 0.18
cot = cot * np.array([1.0, 0.995, 0.985])
save(cot, "tex_c_cotton.jpg", q=90)

M = 480
mott2 = periodic_noise(M, 2.4, 11)
fine = periodic_noise(M, 0.3, 12)
cardb = hexrgb("#F7F4EC")
card = cardb + (mott2[..., None] - 0.5) * 0.02 + (fine[..., None] - 0.5) * 0.03
save(card, "tex_c_card.jpg", q=90)

K = 560
km = periodic_noise(K, 2.0, 21) * 0.6 + periodic_noise(K, 1.0, 22) * 0.4
kf = periodic_fibres(K, 1400, 30, 23, 0.7)
kl = periodic_fibres(K, 700, 26, 24, 0.7)
kraftb = hexrgb("#C2A57B")
kraft = kraftb + (km[..., None] - 0.5) * 0.09 - kf[..., None] * 0.09 + kl[..., None] * 0.07
save(kraft, "tex_c_kraft.jpg", q=90)

# masking tape with torn ends
TW, TH = 260, 64
yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
edge_l = 10 + 6 * np.sin(yy / 3.1) + 3 * np.sin(yy / 1.3 + 1)
edge_r = TW - 10 - 6 * np.sin(yy / 2.7 + 2) - 3 * np.sin(yy / 1.1)
inside = ((xx > edge_l) & (xx < edge_r)).astype(np.float32)
inside = blur(inside, 0.6)
tex = periodic_noise(256, 1.4, 31)
tex = np.asarray(Image.fromarray(tex, mode="F").resize((TW, TH), Image.BICUBIC))
tape_rgb = hexrgb("#E9DFC7") + (tex[..., None] - 0.5) * 0.06
save_rgba(tape_rgb, inside * (0.80 + (tex - 0.5) * 0.12), "tex_c_tape.png")

# ---------------------------------------------------------------- C · two more warm prints
def warm(n, contrast=1.15, pivot=0.45):
    a = load(n, 1400)
    l = curve(mono(a), contrast, pivot)
    l = l * vignette(*l.shape, 0.16)
    l = l + film_grain(l, 0.03, 0.03)
    lo, md, hi2 = hexrgb("#1F1D1A"), hexrgb("#8D877D"), hexrgb("#F2EBDE")
    t = np.clip(l, 0, 1)[..., None]
    return np.where(t < 0.5, lo + (md - lo) * (t * 2), md + (hi2 - md) * (t * 2 - 1))
save(warm(6), "c_sax_street.jpg")
save(warm(279, 1.2, 0.42), "c_bar_friends.jpg")

# ---------------------------------------------------------------- E · party pictures
def movie_bw(a, contrast=1.45, pivot=0.4, vig=0.25, halo=0.2):
    l = curve(mono(a), contrast, pivot, 0.012, 0.965)
    l = l * vignette(*l.shape, vig)
    bright = np.clip((l - 0.72) / 0.28, 0, 1)
    l = l + blur(bright, 11) * halo
    l = l + film_grain(l, 0.04, 0.05)
    lo, hi3 = hexrgb("#0E0E0D"), hexrgb("#F4F1EA")
    return lo + (hi3 - lo) * np.clip(l, 0, 1)[..., None]

def moody_colour(a, vig=0.25):
    l = mono(a)
    c = a * 0.84 + l[..., None] * 0.16
    c = np.stack([curve(c[..., i], 1.15, 0.45) for i in range(3)], -1)
    l2 = np.clip(mono(c), 0, 1)
    sh2 = (1 - l2) ** 2.2
    hi4 = l2 ** 2.2
    c = c * (1 - 0.3 * sh2[..., None]) + hexrgb("#16281F") * 0.3 * sh2[..., None]
    c = c * (1 - 0.12 * hi4[..., None]) + hexrgb("#F4D4CA") * 0.12 * hi4[..., None]
    c = c * vignette(*l.shape, vig)[..., None]
    bright = np.clip((l2 - 0.7) / 0.3, 0, 1)
    c = c + blur(bright, 12)[..., None] * np.array([0.24, 0.07, 0.05])
    c = c + film_grain(l2, 0.035, 0.04)[..., None]
    return c

a = load(372, 1600)
save(movie_bw(a, 1.35, 0.4), "e_mirror_bw.jpg")
save(moody_colour(a), "e_mirror_col.jpg")
a = load(304, 1600)
save(movie_bw(a), "e_player_bw.jpg")
save(moody_colour(a), "e_player_col.jpg")
save(movie_bw(load(279, 1600), 1.4, 0.42), "e_bar_bw.jpg")
save(movie_bw(load(8, 1600), 1.35, 0.42), "e_stage_bw.jpg")

# flyposter wall: rough painted plaster
W, H = 1400, 900
wm = np.asarray(Image.fromarray(periodic_noise(1024, 2.3, 41), mode="F").resize((W, H), Image.BICUBIC))
wf = np.asarray(Image.fromarray(periodic_noise(1024, 0.9, 42), mode="F").resize((W, H), Image.BICUBIC))
stains = np.clip((np.asarray(Image.fromarray(periodic_noise(512, 2.8, 43), mode="F").resize((W, H), Image.BICUBIC)) - 0.62) * 3, 0, 1)
wall = hexrgb("#D9D4CA") + (wm[..., None] - 0.5) * 0.10 + (wf[..., None] - 0.5) * 0.06 - stains[..., None] * np.array([0.10, 0.11, 0.12])
save(wall, "tex_e_wall.jpg", q=86)

# poster paper (seamless) and paste wrinkles
P = 512
pm = periodic_noise(P, 2.0, 51)
pf = periodic_noise(P, 0.4, 52)
paper = 0.5 + (pm - 0.5) * 0.25 + (pf - 0.5) * 0.25
save(paper, "tex_e_paper.jpg", q=88)        # neutral grey, used with multiply / soft-light
WW, WH = 700, 980
rr = np.random.default_rng(61)
pts = np.stack([rr.uniform(0, WW, 70), rr.uniform(0, WH, 70)], -1)
vals = rr.uniform(-1, 1, 70)
gx, gy = np.meshgrid(np.arange(0, WW, 2), np.arange(0, WH, 2))
d = (gx[..., None] - pts[None, None, :, 0]) ** 2 + (gy[..., None] - pts[None, None, :, 1]) ** 2
idx = np.argmin(d, axis=-1)
facet = vals[idx].astype(np.float32)
# a gentle slope inside each facet, so planes read as bent paper rather than flat tiles
slope = (gx - pts[idx][..., 0]) * 0.0016 + (gy - pts[idx][..., 1]) * 0.0011
facet = (facet * 0.5 + slope).astype(np.float32)
facet = np.asarray(Image.fromarray(facet, mode="F").resize((WW, WH), Image.BICUBIC))
wr = np.clip(0.5 + facet * 0.12, 0, 1)
wr = blur(wr, 1.2)
save(wr, "tex_e_wrinkle.jpg", q=86)          # mid-grey based, soft-light over pasted posters

print(sorted(os.listdir(OUT)))
