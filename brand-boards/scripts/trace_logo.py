"""Trace the existing M/darbnica circle logo (raster from mdarbnica.lv) into an SVG path."""
import sys
import numpy as np
from PIL import Image, ImageFilter
import potrace

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("L")
w, h = im.size
im = im.resize((w * 2, h * 2), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
a = np.asarray(im).astype(np.float32) / 255
mask = a < 0.5
ys, xs = np.where(mask)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
print("bbox", x0, x1, y0, y1)
bm = potrace.Bitmap(mask)
plist = bm.trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=1.0, opticurve=True, opttolerance=0.2)
# drop the frame potrace returns around the whole bitmap
plist = [c for c in plist if x0 - 5 <= c.start_point.x <= x1 + 5 and y0 - 5 <= c.start_point.y <= y1 + 5]
# normalise into a 100x100 box centred on the ring
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
size = max(x1 - x0, y1 - y0)
s = 100.0 / size
def P(pt):
    return f"{(pt.x - cx) * s + 50:.1f},{(pt.y - cy) * s + 50:.1f}"
parts = []
for curve in plist:
    d = [f"M{P(curve.start_point)}"]
    for seg in curve.segments:
        if seg.is_corner:
            d.append(f"L{P(seg.c)}L{P(seg.end_point)}")
        else:
            d.append(f"C{P(seg.c1)} {P(seg.c2)} {P(seg.end_point)}")
    d.append("Z")
    parts.append("".join(d))
path = "".join(parts)
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path fill-rule="evenodd" d="{path}"/></svg>'
open(out, "w").write(svg)
print(len(plist), "curves", len(path), "chars")
from PIL import ImageDraw
def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(1, n + 1):
        t = i / n
        mt = 1 - t
        out.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0], mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
    return out
R = 600
canvas = np.zeros((R, R), bool)
def Q(pt):
    return ((pt.x - cx) * s * R / 100 + R / 2, (pt.y - cy) * s * R / 100 + R / 2)
for curve in plist:
    pts = [Q(curve.start_point)]
    cur = pts[0]
    for seg in curve.segments:
        if seg.is_corner:
            pts += [Q(seg.c), Q(seg.end_point)]
        else:
            pts += bez(cur, Q(seg.c1), Q(seg.c2), Q(seg.end_point))
        cur = Q(seg.end_point)
    m = Image.new("1", (R, R), 0)
    ImageDraw.Draw(m).polygon(pts, fill=1)
    canvas ^= np.asarray(m).astype(bool)
Image.fromarray(((~canvas) * 255).astype(np.uint8)).save(out.replace(".svg", "_raster.png"))
