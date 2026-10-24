#!/usr/bin/env python3
"""Run one cutout job by name; writes intermediate npz + check sheet to work/muza/cut/.
usage: python3 -I cutrun.py <job> [<job> ...]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from PIL import Image, ImageDraw
from cutlib import *

S = "/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad"
ORIG = S + "/dl/muza/met-orig"
OUT = S + "/work/muza/cut"
os.makedirs(OUT, exist_ok=True)


def poly_mask(h, w, pts):
    """pts in fractions of the *cropped* frame."""
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array([[x * w, y * h] for x, y in pts], np.int32)], 1)
    return m.astype(bool)


def rect(h, w, x0, y0, x1, y1):
    m = np.zeros((h, w), bool)
    m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = True
    return m


def frac_crop(path, fx0, fy0, fx1, fy1):
    W, H = Image.open(path).size
    return (int(fx0 * W), int(fy0 * H), int(fx1 * W), int(fy1 * H))


def to_crop_frac(c, full):
    """convert full-image fractional coords to crop-frame fractions"""
    fx0, fy0, fx1, fy1 = c
    def f(x, y):
        return ((x - fx0) / (fx1 - fx0), (y - fy0) / (fy1 - fy0))
    return f


JOBS = {}


def job(fn):
    JOBS[fn.__name__] = fn
    return fn


@job
def head():
    src = ORIG + "/253057_2.jpg"
    c = (0.12, 0.05, 0.82, 0.90)
    img = load(src, frac_crop(src, *c), maxdim=1498)
    h, w = img.shape[:2]
    f = to_crop_frac(c, None)
    # rod + floor shadow are background
    rod = poly_mask(h, w, [f(0.414, 0.80), f(0.469, 0.80), f(0.469, 0.95), f(0.414, 0.95)])
    rod |= poly_mask(h, w, [(0.418, 0.826), (0.487, 0.865), (0.487, 1.0), (0.418, 1.0)])  # frame fractions
    fgp = poly_mask(h, w, [(0.60, 0.915), (0.66, 0.933), (0.72, 0.943), (0.77, 0.943), (0.79, 0.935), (0.76, 0.915), (0.66, 0.905)])
    unk = poly_mask(h, w, [f(0.555, 0.60), f(0.72, 0.583), f(0.86, 0.60), f(0.86, 0.95), f(0.66, 0.95), f(0.545, 0.70)])
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=40, t_lo=14, far=40, bg_add=rod, fg_add=fgp, unk_add=unk, unk_close=18, debug=dbg)
    return img, rgb, a, dbg, dict(kind="cut")


@job
def dancer():
    src = ORIG + "/255408_0.jpg"
    c = (0.17, 0.12, 0.79, 0.90)
    img = load(src, frac_crop(src, *c), maxdim=1597)
    h, w = img.shape[:2]
    f = to_crop_frac(c, None)
    unk = poly_mask(h, w, [f(0.20, 0.78), f(0.70, 0.78), f(0.72, 0.90), f(0.18, 0.90)])
    foot = poly_mask(h, w, [(0.48, 0.936), (0.54, 0.90), (0.62, 0.872), (0.68, 0.872), (0.715, 0.886),
                            (0.725, 0.905), (0.715, 0.92), (0.68, 0.928), (0.64, 0.934), (0.56, 0.936)])
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=30, t_lo=10, far=30, unk_add=unk, fg_add=foot, debug=dbg)
    return img, rgb, a, dbg, dict(kind="cut")


@job
def bust():
    src = ORIG + "/253055_0.jpg"
    c = (0.07, 0.07, 0.93, 0.92)
    img = load(src, frac_crop(src, *c), maxdim=1593)
    h, w = img.shape[:2]
    f = to_crop_frac(c, None)
    plinth = poly_mask(h, w, [f(0.0, 0.872), f(1.0, 0.872), f(1.0, 1.0), f(0.0, 1.0)])
    lowl = poly_mask(h, w, [(0.08, 0.84), (0.08, 0.855), (0.11, 0.872), (0.20, 0.877), (0.217, 0.892), (0.226, 0.92),
                            (0.25, 0.932), (0.60, 0.932), (0.60, 0.87), (0.30, 0.86)])  # frame fractions: shadowed lower drapery
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=24, t_lo=8, far=260, bg_add=plinth, fg_add=lowl, dw=(0.35, 2.0, 2.0), keep="all", debug=dbg)
    return img, rgb, a, dbg, dict(kind="cut")


@job
def mask():
    src = ORIG + "/247521_0.jpg"
    c = (0.14, 0.0, 0.88, 0.95)
    img = load(src, frac_crop(src, *c), maxdim=1612)
    h, w = img.shape[:2]
    # through-holes (eyes, mouth, suspension hole): very dark compact blobs inside the mask
    L = luminance(img)
    dark = L < 0.12
    from scipy import ndimage as ndi
    lab, n = ndi.label(dark)
    holes = np.zeros_like(dark)
    for k in range(1, n + 1):
        comp = lab == k
        if comp.sum() > 30:
            holes |= comp
    holes = ndi.binary_dilation(holes, iterations=1)
    # grow each hole through connected near-neutral pixels (backdrop seen through the opening)
    labc = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    chroma = np.hypot(labc[..., 1] - 128, labc[..., 2] - 128)
    near = ndi.binary_dilation(holes, iterations=40)
    holes = ndi.binary_propagation(holes, mask=((chroma < 14) & near) | holes)
    holes = ndi.binary_closing(holes, iterations=2)
    lab2, n2 = ndi.label(holes)
    print('  mask holes:', n2, [int(v) for v in ndi.sum(holes, lab2, range(1, n2 + 1))])
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=30, t_lo=8, far=40, holes_keep=holes, dw=(0.05, 2.0, 2.0), debug=dbg)
    return img, rgb, a, dbg, dict(kind="cut")


@job
def capital():
    src = ORIG + "/252548_0.jpg"
    c = (0.12, 0.06, 0.90, 0.95)
    img = load(src, frac_crop(src, *c), maxdim=1571)
    h, w = img.shape[:2]
    T = texture_map(img, 9)
    T = cv2.GaussianBlur(T, (0, 0), 1.5)
    top = poly_mask(h, w, [(0.075, 0.090), (0.12, 0.0915), (0.16, 0.093), (0.20, 0.095), (0.30, 0.100), (0.40, 0.104), (0.41, 0.1045), (0.41, 0.125), (0.075, 0.125)])
    tab = poly_mask(h, w, [(0.0, 0.155), (0.06, 0.165), (0.072, 0.178), (0.075, 0.20), (0.075, 0.26), (0.0, 0.30)])
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=6.5, t_lo=2.0, far=30, D_override=T, fg_erode=6, open_it=5, final_open=4,
                               fg_add=top, bg_add=tab, debug=dbg)
    return img, rgb, a, dbg, dict(kind="cut")


@job
def sphinx():
    src = ORIG + "/248501_0.jpg"
    c = (0.08, 0.06, 0.90, 0.587)
    img = load(src, frac_crop(src, *c), maxdim=1475)
    h, w = img.shape[:2]
    f = to_crop_frac(c, None)
    seed = np.zeros((h, w), bool); b = int(0.03 * min(h, w))
    seed[:b] = True; seed[:int(0.85 * h), :b] = True; seed[:int(0.85 * h), -b:] = True
    slab = poly_mask(h, w, [f(0.285, 0.548), f(0.86, 0.548), f(0.86, 0.587), f(0.285, 0.587)])
    dbg = {}
    rgb, a, B = make_cutout_ws(img, t_hi=26, t_lo=8, far=60, bg_seed=seed, fg_add=slab, fill_holes=False,
                               dw=(0.35, 2.0, 2.0), debug=dbg)
    # straight, hard cut along the bottom frame edge under the slab
    cols = a[-12:, :].max(0) > 0.5
    a[-3:, cols] = 1.0
    return img, rgb, a, dbg, dict(kind="cut")


def checksheet(name, img, rgb, a, dbg):
    h, w = a.shape
    tiles = []
    for bg in (PAL["cream"], PAL["green"], PAL["rose"]):
        tiles.append(composite(rgb, a, bg))
    mk = np.zeros_like(img); mk[..., 1] = dbg["m0"]; mk[..., 0] = dbg.get("bgm", 0)
    if dbg.get("unk") is not None:
        mk[..., 2] = dbg["unk"]
    tiles.append(img * 0.6 + mk * 0.4)
    row = np.concatenate(tiles, 1)
    sc = 1800 / row.shape[1]
    row = cv2.resize(row, (int(row.shape[1] * sc), int(row.shape[0] * sc)), interpolation=cv2.INTER_AREA)
    Image.fromarray((np.clip(row, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/{name}_check.png")
    # edge zooms: 4 crops at 2x around alpha edges
    edge = (a > 0.05) & (a < 0.95)
    ys, xs = np.where(edge)
    zs = []
    if len(ys):
        idx = np.linspace(0, len(ys) - 1, 6).astype(int)
        for k, bg in zip(idx, [PAL["green"], PAL["cream"], PAL["rose"], PAL["green"], PAL["cream"], PAL["green"]]):
            y, x = ys[k], xs[k]
            y0, x0 = max(0, y - 60), max(0, x - 60)
            comp = composite(rgb, a, bg)[y0:y0 + 120, x0:x0 + 120]
            comp = cv2.resize(comp, (300, 300), interpolation=cv2.INTER_NEAREST)
            pad = np.zeros((300, 300, 3), np.float32); pad[:comp.shape[0], :comp.shape[1]] = comp
            zs.append(pad)
        Image.fromarray((np.clip(np.concatenate(zs, 1), 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/{name}_edges.png")


if __name__ == "__main__":
    for name in sys.argv[1:]:
        img, rgb, a, dbg, meta = JOBS[name]()
        np.savez_compressed(f"{OUT}/{name}.npz", img=img, rgb=rgb, a=a)
        checksheet(name, img, rgb, a, dbg)
        print(name, a.shape, "thr", round(float(dbg["thr"]), 2), "fg%", round(float((a > 0.5).mean()) * 100, 1))
