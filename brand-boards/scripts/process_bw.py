"""Round 5: black-and-white versions of the graded flash photos, and neutral light textures.

Usage: python3 -I process_bw.py OUT_DIR photo1.jpg ... [--light light1.jpg ...]
Photos: red-weighted mono mix (bright skin, like on-camera flash on fast B&W film),
a firm S-curve with deep blacks, and fine luminance grain.
Lights: colour removed, brightness kept, for mix-blend-mode: screen.
"""
import sys, os
import numpy as np
from PIL import Image

rng = np.random.default_rng(55)


def bw(a):
    L = a[..., 0] * 0.44 + a[..., 1] * 0.44 + a[..., 2] * 0.12
    k = 1 / (1 + np.exp(-(L - 0.46) * 6.6))
    k0, k1 = 1 / (1 + np.exp(0.46 * 6.6)), 1 / (1 + np.exp(-(0.54) * 6.6))
    S = (k - k0) / (k1 - k0)
    L = 0.55 * S + 0.45 * L
    L = 0.012 + L * 0.975
    g = rng.normal(0, 1, L.shape).astype(np.float32)
    w = 0.45 + 0.55 * (1 - np.abs(2 * np.clip(L, 0, 1) - 1))
    return np.clip(L + g * 0.022 * w, 0, 1)


def mono_light(a):
    mx = a.max(-1)
    lu = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    return np.clip((0.55 * mx + 0.45 * lu) * 1.05, 0, 1)


def save(L, path):
    Image.fromarray((np.stack([L] * 3, -1) * 255 + 0.5).astype(np.uint8)).save(path, quality=86, optimize=True, progressive=True)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    mode = "photo"
    for p in sys.argv[2:]:
        if p == "--light":
            mode = "light"
            continue
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255
        stem = os.path.splitext(os.path.basename(p))[0]
        if mode == "photo":
            save(bw(a), os.path.join(out, stem + "_bw.jpg"))
        else:
            save(mono_light(a), os.path.join(out, stem + "_mono.jpg"))
        print(stem, a.shape[1], a.shape[0], mode)


if __name__ == "__main__":
    main()
