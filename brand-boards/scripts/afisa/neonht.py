"""Halftone masters (black dots on transparent) of the best neon crop (066 square), 1400 px.
positive: dots = shadows (prints like a newspaper photo); glow: dots = light (rebuilds the neon on a dark ground)."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
import neon, ht

NAME = 'neon066_sq'
CELL = 13

if __name__ == '__main__':
    neon.CROPS[NAME] = (neon.CROPS[NAME][0], neon.CROPS[NAME][1], 1400)
    c = neon.crop(NAME)
    t = neon.tone(c, us=1.4, sig=26, s=0.5)
    h, w = t.shape
    M = np.ones((h, w), np.float32)
    pos = 0.05 + 0.88 * (1 - t)
    tg = neon.tone(c, us=2.2, sig=20, s=0.5)
    glow = np.clip((tg - 0.22) / 0.72, 0, 1) ** 1.25 * 0.95   # thin the light-spill halo, keep the tube dense
    glow = np.where(glow < 0.03, 0, glow)
    for tag, T in [('halftone', pos), ('halftone_glow', glow)]:
        cov = ht.screen(np.clip(T, 0, 0.97).astype(np.float32), M, cell=CELL, angle=45)
        kb = ht.save_dots(OUT + f'afisa_{NAME.replace("_sq", "")}_{tag}.png', cov, '#000000')
        np.save(W + f'neoncov_{tag}.npy', cov)
        print(tag, cov.shape, kb, 'KB')
