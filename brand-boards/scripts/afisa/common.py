import glob, json, os
import cv2, numpy as np
S = '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad'
DL = S + '/dl/afisa/'
W = S + '/work/afisa/'
OUT = S + '/assets8/afisa/'
os.makedirs(OUT, exist_ok=True)

# instrument -> (objectID, view index)
INST = {
    'sax':      (503909, 0),
    'trumpet':  (503961, 4),
    'trombone': (504686, 0),
    'bass':     (503176, 3),
    'clarinet': (854790, 0),
    'drum':     (504262, 0),
    'cymbals':  (500589, 0),
}

TONES = {
    'rose':  dict(light='#F2CBC5', mid='#D8606A', dark='#9E2F3A'),
    'green': dict(light='#BFD6C7', mid='#4F8466', dark='#1F4535'),
    'neutral': dict(paper='#F4F1EA', ink='#111110'),
}


def src_path(name):
    oid, n = INST[name]
    return glob.glob(DL + f'i_{oid}_{n}/*')[0]


def meta(oid):
    return json.load(open(DL + f'o_{oid}/obj.json'))


def load_bgr(name):
    im = cv2.imread(src_path(name), cv2.IMREAD_COLOR)
    return im


def hex2bgr(h):
    return np.array([int(h[5:7], 16), int(h[3:5], 16), int(h[1:3], 16)], np.float32)


def k(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
