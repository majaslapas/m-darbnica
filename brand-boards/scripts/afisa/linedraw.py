"""Line drawings from the stencil bitmaps (SS=2 canvas): bold silhouette contour + interior detail lines.
Thin negative cuts become single strokes, broad cuts become outlined shapes. python3 -I linedraw.py [names] [--trace]"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
import stencil as stc
from stx import show, smooth_bin, drop_small

# widths in 2x-canvas pixels
P = {
    'sax':      dict(outer=13, inner=8, thin=22),
    'trumpet':  dict(outer=11, inner=7, thin=18),
    'trombone': dict(outer=11, inner=7, thin=18),
    'bass':     dict(outer=13, inner=8, thin=22),
    'clarinet': dict(outer=9, inner=6, thin=12),
    'drum':     dict(outer=13, inner=8, thin=34),
    'cymbals':  dict(outer=13, inner=9, thin=40),
}


def build_drum_line():
    big, _ = stc.prep('drum')
    S = np.load(W + 'drum_S.npy'); light = np.load(W + 'drum_light.npy')
    S = stc.contour_smooth(cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_OPEN, k(5)) > 0, 14)
    light = cv2.morphologyEx(light.astype(np.uint8), cv2.MORPH_OPEN, k(6)) > 0
    light = stc.contour_smooth(drop_small(light, 4000), 22)
    din = cv2.distanceTransform(S.astype(np.uint8), cv2.DIST_L2, 5)
    outer = S & (din <= 13)
    dl = cv2.distanceTransform(light.astype(np.uint8), cv2.DIST_L2, 5)
    light_line = light & (dl <= 8) & (din > 6)
    rp = np.zeros(S.shape, bool)
    for x1, y1, x2, y2 in np.load(W + 'drum_lines.npy'):
        rp = stc.stroke(rp, [(x1, y1), (x2, y2)], 10.0)
    rp = stc.stroke(rp, np.load(W + "drum_twist.npy"), 14.0)
    rp &= din > 6
    L = outer | light_line | rp
    L = stc.contour_smooth(L, 2.0)
    return big, drop_small(L, 200)


def build(name):
    if name == 'drum':
        return build_drum_line()
    p = P[name]
    st = np.load(W + f'st_{name}.npy')
    big, S = stc.prep(name)
    S = np.load(W + 'cla_S.npy') if name == 'clarinet' else stc.contour_smooth(S, 4.0)
    S8 = S.astype(np.uint8)
    # bold contour hugging the inside of the silhouette
    din = cv2.distanceTransform(S8, cv2.DIST_L2, 5)
    outer = S & (din <= p['outer'])
    # interior negative space (cuts that do not touch the outside)
    C = S & ~st
    C &= din > 2
    # split cuts into thin and broad parts by local width
    rr = p['thin'] // 2
    broad = cv2.morphologyEx(C.astype(np.uint8), cv2.MORPH_OPEN, k(rr)) > 0
    thin = C & ~(cv2.dilate(broad.astype(np.uint8), k(2)) > 0)
    thin = drop_small(thin, 150)
    # thin cuts: centre-line strokes with a uniform weight
    dt = cv2.distanceTransform(thin.astype(np.uint8), cv2.DIST_L2, 5)
    if name == 'clarinet':      # centre-line strokes, so the rod near the edge stays separate from the outline
        import ropes
        thin_line = cv2.dilate(ropes.zhang_suen(thin).astype(np.uint8), k(2)) > 0
    else:
        thin_line = cv2.dilate(thin.astype(np.uint8), k(max(1, p['inner'] // 4))) > 0
    # broad cuts: outline band on their inside
    db = cv2.distanceTransform(broad.astype(np.uint8), cv2.DIST_L2, 5)
    broad_line = broad & (db <= p['inner'])
    L = outer | thin_line | broad_line
    L = stc.contour_smooth(L, 2.5)
    L = drop_small(L, 200)
    return big, L


if __name__ == '__main__':
    names = [n for n in sys.argv[1:] if n in INST] or list(P)
    for n in names:
        big, L = build(n)
        np.save(W + f'line_{n}.npy', L)
        o = np.full(L.shape + (3,), (234, 241, 244), np.uint8); o[L] = (16, 17, 17)
        show([o], W + f'prev/line_{n}.jpg', 900 if L.shape[0] > L.shape[1] else 420)
        if '--trace' in sys.argv:
            stc.trace_svg(L, OUT + f'afisa_{n}_line.svg', alphamax=1.1, opttol=0.8, dec=0 if n == 'drum' else 1)
