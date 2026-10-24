#!/usr/bin/env python3
"""Export final Muza assets (3 treatments each) to assets8/muza.
usage: python3 -I export.py [name ...]   (default: all)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from cutlib import *

S = "/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad"
W = S + "/work/muza"
OUT = S + "/assets8/muza"
MET = S + "/dl/muza/met-orig"
COM = S + "/dl/muza/commons-orig2"
os.makedirs(OUT, exist_ok=True)
MAXB = 900 * 1024

# name, kind, source, crop (fractions x0,y0,x1,y1) or None, grading options
ASSETS = [
    dict(name="muza_head_profile", kind="cut", src="head"),
    dict(name="muza_dancer_bronze", kind="cut", src="dancer", nat=dict(hi_cap=0.62),
         green=dict(target=0.46), rose=dict(target=0.42)),
    dict(name="muza_bust_veiled", kind="cut", src="bust"),
    dict(name="muza_mask_tragic", kind="cut", src="mask", fix="ink", nat=dict(sat=0.74)),
    dict(name="muza_capital_pilaster", kind="cut", src="capital", nat=dict(warmth=0.06)),
    dict(name="muza_sphinx_archaic", kind="cut", src="sphinx"),
    dict(name="muza_vase_kitharode", kind="crop", src=MET + "/254896_6.jpg", crop=(0.08, 0.0, 0.84, 1.0),
         green=dict(target=None), rose=dict(target=None)),
    dict(name="muza_fresco_kithara", kind="crop", src=MET + "/247009_2.jpg", crop=(0.04, 0.0, 0.96, 1.0)),
    dict(name="muza_fresco_redfield", kind="crop", src=MET + "/247009_0.jpg", crop=(0.51, 0.095, 0.93, 0.255)),
    dict(name="muza_facade_alberta13_mask", kind="crop", src=COM + "/detail_150502-51.jpg", crop=(0.0, 0.07, 1.0, 0.83)),
    dict(name="muza_facade_alberta2a_sphinx", kind="crop", src=COM + "/art_nouveau_riga_31.jpg", crop=(0.64, 0.06, 0.985, 0.66)),
    dict(name="muza_facade_alberta13_peacock", kind="crop", src=COM + "/detail_150502-60.jpg", crop=(0.10, 0.07, 0.92, 0.92)),
    dict(name="muza_facade_alberta13_winged", kind="crop", src=COM + "/detail_150502-41.jpg", crop=(0.16, 0.02, 0.84, 0.44)),
    dict(name="muza_facade_elizabetes33_atlas", kind="crop", src=COM + "/detail_150502-53.jpg", crop=(0.04, 0.03, 0.96, 0.82)),
]


def fix_ink(rgb, a):
    R, G = rgb[..., 0], rgb[..., 1]
    ink = (R > 0.25) & (R / (G + 0.02) > 2.4) & (a > 0.5)
    lab, n = ndi.label(ndi.binary_dilation(ink, iterations=6))
    if n:
        sizes = ndi.sum(ink, lab, range(1, n + 1))
        ink = ink & (lab == (np.argmax(sizes) + 1))
    m = ndi.binary_dilation(ink, iterations=3).astype(np.uint8) * 255
    u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    fixed = cv2.inpaint(u8, m, 7, cv2.INPAINT_TELEA).astype(np.float32) / 255
    # re-add grain so the patch does not look smeared
    rng = np.random.default_rng(1)
    grain = rng.normal(0, 0.018, fixed.shape[:2]).astype(np.float32)[..., None]
    mm = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.5)[..., None]
    return np.clip(fixed + grain * mm, 0, 1)


def natural(rgb, a=None, hi_cap=None, **kw):
    # cap the highlight stretch so dark objects (bronze) are not lifted into grey
    L = luminance(rgb)
    m = (a > 0.9) if a is not None else np.ones(L.shape, bool)
    lo = min(np.percentile(L[m], 0.3), 0.10)
    hi = np.percentile(L[m], 99.8)
    if hi_cap is not None:
        hi = max(hi, hi_cap)
    hi = max(hi, 0.80) if hi_cap is None else hi
    return _nat(rgb, a, lo, hi, **kw)


def _nat(rgb, a, lo, hi, sat=0.88, warmth=0.035, k=0.12):
    ink = PAL["ink"]
    white = np.array([0.975, 0.955, 0.915], np.float32)
    x = rgb.astype(np.float32)
    lin = srgb2lin(x) * np.array([1 + warmth, 1.0, 1 - 1.6 * warmth], np.float32)
    x = lin2srgb(lin)
    lab = lin2oklab(srgb2lin(x)); lab[..., 1:] *= sat
    x = lin2srgb(oklab2lin(lab))
    L = luminance(x)
    Ln = scurve(np.clip((L - lo) / max(hi - lo, 1e-4), 0, 1), k)
    lab = lin2oklab(srgb2lin(x))
    lab[..., 0] *= np.clip((Ln + 1e-4) / (L + 1e-4), 0, 3)
    x = lin2srgb(oklab2lin(lab))
    x = ink + (white - ink) * np.clip(x, 0, 1)
    return np.clip(x, 0, 1).astype(np.float32)


def treatments(rgb, a, opts):
    nat = natural(rgb, a, **opts.get("nat", {}))
    g = opts.get("green", {}); r = opts.get("rose", {})
    tg = duotone_t(rgb, a, gamma=g.get("gamma", 1.0), k=g.get("k", 0.22), lo_p=g.get("lo_p", 0.8),
                   hi_p=g.get("hi_p", 99.6), target=g.get("target", 0.55))
    tr = duotone_t(rgb, a, gamma=r.get("gamma", 1.0), k=r.get("k", 0.22), lo_p=r.get("lo_p", 0.8),
                   hi_p=r.get("hi_p", 99.6), target=r.get("target", 0.50))
    green = make_ramp(PAL["green"], PAL["cream"])(tg)
    rose = make_ramp(PAL["ink"], PAL["rose"])(tr)
    return dict(natural=nat, green=green, rose=rose)


def rs(x, sc):
    if sc >= 0.999:
        return x
    h, w = x.shape[:2]
    return cv2.resize(x, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)


def save_png_capped(path, rgb, a):
    size = save_rgba(path, rgb, a)
    sc = 1.0
    while os.path.getsize(path) > MAXB and sc > 0.6:
        sc *= 0.92
        h, w = a.shape
        r2 = cv2.resize(rgb, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
        a2 = cv2.resize(a, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
        size = save_rgba(path, r2, a2)
    return size


def save_jpg_capped(path, rgb):
    q = 85
    size = save_jpg(path, rgb, q)
    while os.path.getsize(path) > MAXB and q > 70:
        q -= 3
        size = save_jpg(path, rgb, q)
    return size, q


def run(asset):
    name = asset["name"]
    res = []
    if asset["kind"] == "cut":
        d = np.load(f"{W}/cut/{asset['src']}.npz")
        rgb, a = d["rgb"], d["a"]
        if asset.get("fix") == "ink":
            rgb = fix_ink(rgb, a)
        nat = natural(rgb, a, **asset.get("nat", {}))
        g = asset.get("green", {}); r = asset.get("rose", {})
        tg = duotone_t(rgb, a, gamma=g.get("gamma", 1.0), k=g.get("k", 0.22), lo_p=g.get("lo_p", 0.8), hi_p=g.get("hi_p", 99.6),
                       target=g.get("target", 0.55))
        tr = duotone_t(rgb, a, gamma=r.get("gamma", 1.0), k=r.get("k", 0.22), lo_p=r.get("lo_p", 0.8), hi_p=r.get("hi_p", 99.6),
                       target=r.get("target", 0.50))
        jobs = [("cut", lambda p, sc: save_indexed_natural(p, rs(nat, sc), rs(a, sc))),
                ("green", lambda p, sc: save_indexed_ramp(p, rs(tg, sc), rs(a, sc), make_ramp(PAL["green"], PAL["cream"]))),
                ("rose", lambda p, sc: save_indexed_ramp(p, rs(tr, sc), rs(a, sc), make_ramp(PAL["ink"], PAL["rose"])))]
        scales = []
        for suffix, fn in jobs:
            p = f"{OUT}/{name}_{suffix}.png"
            sc = 1.0
            sz = fn(p, sc)
            while os.path.getsize(p) > MAXB and sc > 0.6:
                sc *= 0.97
                sz = fn(p, sc)
            scales.append(sc)
        sc = min(scales)  # all variants of one asset share identical dimensions
        for suffix, fn in jobs:
            p = f"{OUT}/{name}_{suffix}.png"
            sz = fn(p, sc)
            res.append((os.path.basename(p), sz, os.path.getsize(p)))
    else:
        im = Image.open(asset["src"]).convert("RGB")
        W_, H_ = im.size
        x0, y0, x1, y1 = asset["crop"]
        img = load(asset["src"], (int(x0 * W_), int(y0 * H_), int(x1 * W_), int(y1 * H_)), maxdim=1400)
        T = treatments(img, None, asset)
        for key in ("natural", "green", "rose"):
            p = f"{OUT}/{name}_{key}.jpg"
            sz, q = save_jpg_capped(p, T[key])
            res.append((os.path.basename(p), sz, os.path.getsize(p)))
    for r in res:
        print(f"{r[0]:52s} {r[1][0]}x{r[1][1]}  {r[2]//1024} KB")
    return res


if __name__ == "__main__":
    names = sys.argv[1:]
    allres = {}
    for a in ASSETS:
        if names and a["name"] not in names:
            continue
        allres[a["name"]] = run(a)
    man = f"{W}/manifest.json"
    old = json.load(open(man)) if os.path.exists(man) else {}
    old.update({k: [[r[0], list(r[1]), r[2]] for r in v] for k, v in allres.items()})
    json.dump(old, open(man, "w"), indent=1)
