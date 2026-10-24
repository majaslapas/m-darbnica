"""Neon logo crops (066 singer, 076 guitarist), tone-on-tone duotones and halftone masters.
python3 -I neon.py [crops] [duo] [ht]"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *

SRC = {'066': S + '/dl/flash_src/066.jpg', '076': S + '/dl/flash_src/076.jpg'}
# (x, y, w, h) in the 3500x2336 originals, output long side
CROPS = {
    'neon066_sq': ('066', (1155, 25, 1180, 1180), 1200),
    'neon066_pt': ('066', (1255, 0, 1000, 1250), 1200),
    'neon076_sq': ('076', (780, 20, 1180, 1180), 1200),
    'neon076_pt': ('076', (800, 0, 960, 1200), 1200),
}
FAM = {
    'rose':  ('#9E2F3A', '#D8606A', '#F2CBC5'),
    'green': ('#1F4535', '#4F8466', '#BFD6C7'),
}


def crop(name):
    src, (x, y, w, h), long = CROPS[name]
    im = cv2.imread(SRC[src])
    c = im[y:y + h, x:x + w]
    s = long / max(w, h)
    return cv2.resize(c, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def tone(c, lo=22, hi=236, wl=0.25, us=1.6, sig=22, s=0.6, gamma=1.15):
    """0..1 'brightness' where red neon counts as light: mostly the red channel plus a little luminance,
    denoised, with local contrast at the neon-tube scale and an S-curve."""
    f = cv2.bilateralFilter(c, 9, 30, 5).astype(np.float32)
    R = f[..., 2]
    lum = 0.2126 * f[..., 2] + 0.7152 * f[..., 1] + 0.0722 * f[..., 0]
    v = cv2.GaussianBlur((1 - wl) * R + wl * lum, (0, 0), 0.8)
    t = np.clip((v - lo) / (hi - lo), 0, 1) ** gamma
    t = np.clip(t + us * (t - cv2.GaussianBlur(t, (0, 0), sig)), 0, 1)
    t = (1 - s) * t + s * (t * t * (3 - 2 * t))
    return np.clip(t, 0, 1)


def lab_of(hexes):
    px = np.array([[hex2bgr(h) for h in hexes]], np.float32) / 255
    return cv2.cvtColor(px, cv2.COLOR_BGR2LAB)[0]


def gradient_map(t, fam, mid_w=1.0):
    """t (0..1) -> colours along dark -> mid -> light in Lab; mid_w=0 gives a straight two-colour duotone."""
    d, m, l = lab_of(FAM[fam])
    lin = d + (l - d) * 0.5
    mm = lin + mid_w * (m - lin)
    t3 = t[..., None]
    lo_ = d + (mm - d) * np.clip(t3 * 2, 0, 1)
    hi_ = mm + (l - mm) * np.clip(t3 * 2 - 1, 0, 1)
    lab = np.where(t3 < 0.5, lo_, hi_).astype(np.float32)
    bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return np.clip(bgr * 255, 0, 255).round().astype(np.uint8)


def save_jpg(path, im, q=88):
    cv2.imwrite(path, im, [cv2.IMWRITE_JPEG_QUALITY, q, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    return os.path.getsize(path) // 1024


if __name__ == '__main__':
    acts = sys.argv[1:] or ['crops', 'duo']
    for name in CROPS:
        c = crop(name)
        if 'crops' in acts:
            print(name, c.shape, save_jpg(OUT + f'afisa_{name}.jpg', c), 'KB')
        if 'duo' in acts:
            t = tone(c)
            np.save(W + f't_{name}.npy', t)
            for fam in FAM:
                g = gradient_map(t, fam)
                print(' ', fam, save_jpg(OUT + f'afisa_{name}_{fam}.jpg', g), 'KB')
