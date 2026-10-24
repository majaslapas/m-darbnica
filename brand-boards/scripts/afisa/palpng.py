"""Palette PNG with alpha that keeps photos smooth: 225 median-cut colours + Floyd-Steinberg for opaque pixels,
edge pixels get (5 colours x 6 alpha levels) entries, one fully transparent entry."""
import numpy as np
from PIL import Image

N_OPAQUE, N_EDGE_COL, ALPHA_LEVELS = 225, 5, (36, 73, 109, 146, 182, 219)


def save_pal_rgba(path, rgba):
    """rgba: HxWx4 uint8 in RGBA order."""
    h, w = rgba.shape[:2]
    a = rgba[..., 3]
    rgb = rgba[..., :3].copy()
    opaque = a >= 248
    edge = (a >= 8) & ~opaque
    # opaque palette from opaque pixels only (strip image)
    px = rgb[opaque]
    strip = Image.fromarray(px.reshape(1, -1, 3), 'RGB')
    pal_img = strip.quantize(colors=N_OPAQUE, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(pal_img.getpalette()[:N_OPAQUE * 3], np.uint8).reshape(-1, 3)
    # dithered assignment of the full image against that palette (transparent area filled with mean colour)
    fill = rgb.copy(); fill[~opaque] = px.mean(0).astype(np.uint8)
    pimg = Image.new('P', (1, 1)); pimg.putpalette(pal.flatten().tolist() + [0] * (768 - pal.size))
    q = np.array(Image.fromarray(fill, 'RGB').quantize(palette=pimg, dither=Image.Dither.FLOYDSTEINBERG), np.uint8)
    q = np.minimum(q, N_OPAQUE - 1)
    # edge colours: k-means-ish via median cut on edge pixels
    epx = rgb[edge] if edge.any() else px[:10]
    ep = Image.fromarray(epx.reshape(1, -1, 3), 'RGB').quantize(colors=N_EDGE_COL, method=Image.Quantize.MEDIANCUT)
    ecols = np.array(ep.getpalette()[:N_EDGE_COL * 3], np.uint8).reshape(-1, 3)
    full_pal = np.zeros((256, 3), np.uint8); trns = np.full(256, 255, np.uint8)
    full_pal[:N_OPAQUE] = pal
    idx = N_OPAQUE
    lut = {}
    for ci in range(N_EDGE_COL):
        for li, al in enumerate(ALPHA_LEVELS):
            full_pal[idx] = ecols[ci]; trns[idx] = al; lut[(ci, li)] = idx; idx += 1
    TRANSP = 255
    full_pal[TRANSP] = 0; trns[TRANSP] = 0
    out = q.copy()
    if edge.any():
        e_rgb = rgb[edge].astype(np.int32)
        d = ((e_rgb[:, None, :] - ecols[None, :, :].astype(np.int32)) ** 2).sum(-1)
        ci = d.argmin(1)
        li = np.abs(a[edge][:, None].astype(np.int32) - np.array(ALPHA_LEVELS)[None, :]).argmin(1)
        out[edge] = N_OPAQUE + ci * len(ALPHA_LEVELS) + li
    out[a < 8] = TRANSP
    im = Image.fromarray(out, 'P')
    im.putpalette(full_pal.flatten().tolist())
    im.save(path, optimize=True, transparency=trns.tobytes())
