import sys, os
import numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
im = Image.open(os.path.join(src, "371.jpg")).convert("RGB")
im.thumbnail((1500, 1500), Image.LANCZOS)
a = np.asarray(im).astype(np.float32) / 255
l = a[..., 0] * 0.36 + a[..., 1] * 0.5 + a[..., 2] * 0.14
c = a * 0.9 + l[..., None] * 0.1
c = c * np.array([1.02, 1.0, 0.95])
h, w = l.shape
y, x = np.mgrid[0:h, 0:w].astype(np.float32)
d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / 1.414
c = c * (1 - 0.18 * np.clip(d, 0, 1) ** 2)[..., None]
c = c + np.random.default_rng(3).normal(0, 0.03, (h, w, 1)).astype(np.float32)
Image.fromarray((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, "c_courtyard_col.jpg"), quality=82, optimize=True, progressive=True)
print(im.size)
