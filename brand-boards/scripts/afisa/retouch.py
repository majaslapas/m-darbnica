"""Retouch the painted maker's character off the front bo cymbal (work-res image) by rotating a patch of the same
flange ring onto it (in ellipse->circle space), tone-matched and feathered. Writes work_cymbals_rt.png.
python3 -I retouch.py <angle_deg>"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
from scipy import ndimage as ndi
from stx import base

ang = float(sys.argv[1]) if len(sys.argv) > 1 else -28.0
b = cv2.imread(W + 'work_cymbals.png'); fg = np.load(W + 'fg_cymbals.npy'); h, w = fg.shape
# front-cymbal ellipse: canvas coords -> work coords
_, _, s, (ox, oy) = base('cymbals')
cx, cy, ax, ay, ea = np.load(W + 'cym_front_ellipse.npy')
cxw, cyw = cx / s + ox, cy / s + oy
axw, ayw = ax / s, ay / s
# character mask
L = cv2.cvtColor(b, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
box = np.zeros((h, w), bool); box[1190:1425, 1240:1470] = True
ch = (L < 30) & box & fg
ch = cv2.morphologyEx(ch.astype(np.uint8), cv2.MORPH_CLOSE, k(4)) > 0
ch = ndi.binary_fill_holes(ch)
mask = cv2.dilate(ch.astype(np.uint8), k(10)).astype(np.float32)
feather = cv2.GaussianBlur(mask, (0, 0), 6)
# affine: rotate by `ang` about the centre in circle space
th = np.deg2rad(ea)
Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
Sm = np.diag([1.0, axw / ayw]) if axw < ayw else np.diag([ayw / axw, 1.0])
Sm = Rm @ np.diag([1.0, axw / ayw]) @ Rm.T            # stretch along the ellipse's own axes
ra = np.deg2rad(ang)
Rot = np.array([[np.cos(ra), -np.sin(ra)], [np.sin(ra), np.cos(ra)]])
A = np.linalg.inv(Sm) @ Rot @ Sm                      # dest -> source sampling matrix
c = np.array([cxw, cyw])
M = np.hstack([A, (c - A @ c)[:, None]]).astype(np.float32)
src = cv2.warpAffine(b, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
# tone match: mean/std per Lab channel within a ring around the patch
ring = (cv2.dilate(mask.astype(np.uint8), k(30)) > 0) & ~(mask > 0) & fg
lab_b = cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(np.float32); lab_s = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32)
srcmask = (cv2.warpAffine(mask, M, (w, h), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP) > 0)
inner = mask > 0
for ci in range(3):
    mt, st_ = lab_b[..., ci][ring].mean(), lab_b[..., ci][ring].std()
    ms, ss = lab_s[..., ci][inner].mean(), lab_s[..., ci][inner].std()
    lab_s[..., ci] = (lab_s[..., ci] - ms) * (st_ / max(ss, 1e-3)) * 0.9 + mt
# low-frequency shading: replace the patch's smooth component with an interpolation of the surroundings
blurL = cv2.GaussianBlur(np.where(inner[..., None], 0, lab_b), (0, 0), 25)
wts = cv2.GaussianBlur((~inner).astype(np.float32), (0, 0), 25)[..., None]
surround = blurL / np.maximum(wts, 1e-3)
lowS = cv2.GaussianBlur(lab_s, (0, 0), 25)
lab_s = lab_s - lowS + surround
out = cv2.cvtColor(np.clip(lab_s, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
res = (b * (1 - feather[..., None]) + out * feather[..., None]).astype(np.uint8)
cv2.imwrite(W + 'work_cymbals_rt.png', res)
y0, y1, x0, x1 = 1050, 1600, 1050, 1650
cv2.imwrite(W + f'prev/rt_{int(ang)}.jpg', np.concatenate([b[y0:y1, x0:x1], res[y0:y1, x0:x1]], 1))
print('ellipse work', round(cxw), round(cyw), round(axw), round(ayw), 'char px', int(ch.sum()))
