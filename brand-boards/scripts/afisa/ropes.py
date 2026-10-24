"""Drum rope redraw: rope mask -> Zhang-Suen skeleton -> Hough segments -> merged straight ropes."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-m-darbnica/96dd5ec8-e7db-5f60-8e95-0d41c8c379e8/scratchpad/work/afisa')
from common import *
from scipy import ndimage as ndi


def zhang_suen(img):
    """Vectorised Zhang-Suen thinning of a bool image."""
    I = np.pad(img.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P2 = I[:-2, 1:-1]; P3 = I[:-2, 2:]; P4 = I[1:-1, 2:]; P5 = I[2:, 2:]
            P6 = I[2:, 1:-1]; P7 = I[2:, :-2]; P8 = I[1:-1, :-2]; P9 = I[:-2, :-2]
            C = I[1:-1, 1:-1]
            nb = [P2, P3, P4, P5, P6, P7, P8, P9]
            B = sum(n.astype(np.int32) for n in nb)
            seq = nb + [P2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int32) for i in range(8))
            if step == 0:
                m = (C == 1) & (B >= 2) & (B <= 6) & (A == 1) & ((P2 * P4 * P6) == 0) & ((P4 * P6 * P8) == 0)
            else:
                m = (C == 1) & (B >= 2) & (B <= 6) & (A == 1) & ((P2 * P4 * P8) == 0) & ((P2 * P6 * P8) == 0)
            if m.any():
                I[1:-1, 1:-1][m] = 0
                changed = True
        if not changed:
            break
    return I[1:-1, 1:-1] > 0


def merge_segments(segs, ang_tol=4.0, off_tol=10.0, gap=40.0):
    """Greedy merge of collinear Hough segments. segs: (N,4) x1,y1,x2,y2."""
    segs = [np.array(s, np.float64) for s in segs]
    def params(s):
        x1, y1, x2, y2 = s
        a = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
        n = np.array([-np.sin(np.radians(a)), np.cos(np.radians(a))])
        off = n @ np.array([x1, y1])
        return a, off
    changed = True
    while changed:
        changed = False
        out = []
        used = [False] * len(segs)
        for i in range(len(segs)):
            if used[i]:
                continue
            si = segs[i]; ai, oi = params(si)
            for j in range(i + 1, len(segs)):
                if used[j]:
                    continue
                sj = segs[j]; aj, oj = params(sj)
                da = min(abs(ai - aj), 180 - abs(ai - aj))
                if da > ang_tol:
                    continue
                # offset of sj endpoints from si's line
                n = np.array([-np.sin(np.radians(ai)), np.cos(np.radians(ai))])
                d1 = abs(n @ sj[:2] - oi); d2 = abs(n @ sj[2:] - oi)
                if max(d1, d2) > off_tol:
                    continue
                # projection overlap / gap along direction
                t = np.array([np.cos(np.radians(ai)), np.sin(np.radians(ai))])
                pi = sorted([t @ si[:2], t @ si[2:]]); pj = sorted([t @ sj[:2], t @ sj[2:]])
                if pj[0] > pi[1] + gap or pi[0] > pj[1] + gap:
                    continue
                pts = np.array([si[:2], si[2:], sj[:2], sj[2:]])
                pr = pts @ t
                a_, b_ = pts[np.argmin(pr)], pts[np.argmax(pr)]
                # refit: keep line through weighted mean
                si = np.array([a_[0], a_[1], b_[0], b_[1]]); ai, oi = params(si)
                used[j] = True; changed = True
            out.append(si)
        segs = out
    return np.array(segs)
