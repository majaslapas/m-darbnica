"""C · Partitūra: colour twin of the sax-street print for the website reveal."""
import sys, os
import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(41)

im = Image.open(os.path.join(SRC, "006.jpg")).convert("RGB")
im.thumbnail((1400, 1400), Image.LANCZOS)
a = np.asarray(im).astype(np.float32) / 255.0
l = a[..., 0] * 0.36 + a[..., 1] * 0.5 + a[..., 2] * 0.14
c = a * 0.88 + l[..., None] * 0.12              # a little muted, like an old colour print
c = c * np.array([1.03, 1.0, 0.93], np.float32)  # warm paper cast
c = 0.03 + c * 0.95                              # lifted blacks
h, w = l.shape
y, x = np.mgrid[0:h, 0:w].astype(np.float32)
d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
c = c * (1 - 0.16 * np.clip(d, 0, 1) ** 2)[..., None]
c = c + rng.normal(0, 0.028, (h, w, 1)).astype(np.float32)
Image.fromarray((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
    os.path.join(OUT, "c_sax_street_col.jpg"), quality=84, optimize=True, progressive=True)
print(im.size)
