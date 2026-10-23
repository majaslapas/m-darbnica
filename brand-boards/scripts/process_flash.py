"""Round 4: hard on-camera-flash film grade for colour event photos.

Usage: python3 -I process_flash.py OUT_DIR SRC.jpg[:name[:maxedge[:strength]]] ...
Bright frontal subject, background falling off to black, punchy colour with a film
split tone (warm highlights, teal-green shadows), red halation round highlights and grain.
"""
import sys, os
import numpy as np
import cv2
from PIL import Image

rng = np.random.default_rng(404)


def blur(a, r):
    a = np.asarray(a, np.float32)
    return cv2.GaussianBlur(a, (0, 0), sigmaX=float(r), sigmaY=float(r), borderType=cv2.BORDER_REFLECT)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def flash(a):
    h, w = a.shape[:2]
    L = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    # background falloff: what is dim in a wide neighbourhood goes darker
    Lb = blur(L, max(h, w) / 40)
    fall = 0.5 + 0.5 * smooth(0.05, 0.34, Lb)
    gain = 1.1 + 0.16 * smooth(0.2, 0.55, Lb)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 1.414
    vig = 1 - 0.34 * np.clip(d, 0, 1) ** 2.2
    # contrast curve on luminance, applied as a ratio to keep hue
    gain = 1 + (gain - 1) * (1 - smooth(0.5, 0.85, L))
    Lc = np.clip(L * fall * gain * vig, 0, 1)
    k = 1 / (1 + np.exp(-(Lc - 0.4) * 7.0))
    k0, k1 = 1 / (1 + np.exp(0.4 * 7.0)), 1 / (1 + np.exp(-(0.6) * 7.0))
    Lt = (k - k0) / (k1 - k0)
    Lt = 0.62 * Lt + 0.38 * np.clip(Lc * 1.15, 0, 1)
    Lt = np.where(Lt > 0.82, 0.82 + (1 - np.exp(-(Lt - 0.82) * 3.0)) * 0.18, Lt)  # soft shoulder
    rgb = a * (Lt / np.maximum(L, 1e-4))[..., None]
    # saturation boost
    Ln = (rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11)[..., None]
    rgb = Ln + (rgb - Ln) * 1.26
    # split tone
    sh = np.array([0.02, 0.10, 0.10], np.float32)
    hi = np.array([1.035, 0.995, 0.93], np.float32)
    t = np.clip(Ln, 0, 1)
    rgb = rgb * (1 - t) + rgb * hi * t + sh * (1 - t) ** 3 * 0.55
    # halation round the brightest bits
    hl = np.clip((Ln[..., 0] - 0.88) / 0.12, 0, 1)
    hal = blur(hl, max(h, w) / 160)
    rgb = 1 - (1 - rgb) * (1 - hal[..., None] * np.array([0.2, 0.06, 0.02], np.float32))
    # film base and grain
    rgb = 0.018 + rgb * 0.975
    g = rng.normal(0, 1, (h, w)).astype(np.float32)
    g = 0.7 * g + 0.3 * blur(g, 1.2) * 2.2
    Lg = np.clip(rgb.mean(-1), 0, 1)
    gw = 0.45 + 0.55 * (1 - np.abs(2 * Lg - 1))
    rgb = rgb + (g * 0.03 * gw)[..., None] + rng.normal(0, 0.006, (h, w, 3)).astype(np.float32)
    return np.clip(rgb, 0, 1)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for spec in sys.argv[2:]:
        parts = spec.split(":")
        src = parts[0]
        name = parts[1] if len(parts) > 1 and parts[1] else os.path.splitext(os.path.basename(src))[0] + "_flash"
        edge = int(parts[2]) if len(parts) > 2 and parts[2] else 1600
        strength = float(parts[3]) if len(parts) > 3 else 1.0
        im = Image.open(src).convert("RGB")
        im.thumbnail((edge, edge), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255
        r = flash(a)
        if strength < 1:
            r = np.clip(a * (1 - strength) + r * strength, 0, 1)
        Image.fromarray((r * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, name + ".jpg"), quality=86, optimize=True, progressive=True)
        print(name, im.size)


if __name__ == "__main__":
    main()
