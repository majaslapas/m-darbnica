"""Logo halftone masters (black dots on transparent), 1400x1400, from the browser-rasterised S/logo/m_logo.svg.
glow : strokes in near-solid dots + a halo of shrinking dots (neon-in-print)
tint : dots clipped to the strokes, gentle diagonal tone gradient, crisp edges"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
import ht

CELL = 12


def logo_canvas(pad):
    cov = np.load(W + 'logo_cov.npy')                      # 1400x1400, logo spans the full square
    cov = cv2.copyMakeBorder(cov, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    return cv2.resize(cov, (1400, 1400), interpolation=cv2.INTER_AREA)


if __name__ == '__main__':
    # glow
    c = logo_canvas(84)
    m = c > 0.5
    dout = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    T = np.where(m, 0.93, 0.62 * np.exp(-dout / 20.0)).astype(np.float32)
    cov = ht.screen(np.clip(T, 0, 0.97), np.ones_like(T), cell=CELL, angle=45)
    print('glow', ht.save_dots(OUT + 'afisa_logo_halftone.png', cov), 'KB')
    np.save(W + 'logoht_glow.npy', cov)
    # tint
    c = logo_canvas(24)
    m = c > 0.5
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    diag = np.clip((xx / w) * 0.5 + (1 - yy / h) * 0.5, 0, 1)
    T = np.where(m, 0.97 - 0.45 * diag, 0).astype(np.float32)
    cov = ht.screen(np.clip(T, 0, 0.97), c.astype(np.float32), cell=CELL, angle=45)
    cov = cov * cv2.GaussianBlur(c, (0, 0), 0.7)
    print('tint', ht.save_dots(OUT + 'afisa_logo_halftone_tint.png', cov), 'KB')
    np.save(W + 'logoht_tint.npy', cov)
