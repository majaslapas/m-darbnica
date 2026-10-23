import sys, os
import numpy as np
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
def halftone(name, outname, cell=7, scale=3, gamma=1.8):
    im = Image.open(os.path.join(src, name)).convert("L")
    w, h = im.size
    gw, gh = w // cell, h // cell
    small = np.asarray(im.resize((gw, gh), Image.LANCZOS)).astype(np.float32) / 255
    W, H = gw * cell * scale // 2, gh * cell * scale // 2
    c = cell * scale / 2
    canvas = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(canvas)
    for y in range(gh):
        for x in range(gw):
            dark = (1 - small[y, x]) ** gamma
            r = c * 0.64 * dark ** 0.75
            if r < 0.4:
                continue
            cx, cy = (x + 0.5) * c, (y + 0.5) * c
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    a = np.asarray(canvas)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0:3] = 17
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(os.path.join(out, outname), optimize=True)
    print(outname, W, H)
halftone("e_hat_bw.jpg", "e_hat_halftone.png", cell=8)
halftone("e_drummer_bw.jpg", "e_drummer_halftone.png", cell=8)
