#!/usr/bin/env python3
"""
VOXEL BOUQUET  -  a 3D brick-built flower bouquet
=================================================

A real-time 3D LEGO-style flower bouquet built entirely from square blocks,
rendered with glossy plastic, studs, brick seams and soft shadows, rotating
a full 360 degrees. Add a tiny gift tag and write your own message on it.

Install (once)
--------------
    pip install pygame-ce moderngl numpy

Run
---
    python voxel_bouquet.py

    Options:  --text "HAPPY BIRTHDAY"   --no-tag   --speed 30
              --size 1600x1000   --maximized   --fullscreen

Controls (also shown in the app: click  ?  or press H)
--------
    Mouse     drag = turn the bouquet, scroll = zoom, double-click = reset
    Tab       show / hide the tag (animated)
    Enter     write your message on the tag (Enter = apply, Esc = cancel)
    C         close-up of the tag
    Space     pause / play          Left / Right   slower / faster
    R         reverse direction     S              shadows on / off
    F         fullscreen            M              maximise
    [ / ]     smaller / bigger      0              reset view
    Q         quit

The control bar at the bottom is clickable and fades away when you are not
using the mouse. Everything you may want to change is in PARAMETERS below.
"""

import argparse
import math
import sys
import time

import numpy as np

# =============================================================================
#  PARAMETERS
# =============================================================================
WINDOW_SIZE = (1280, 860)
TARGET_FPS = 60
MSAA_SAMPLES = 4
ROTATION_SPEED_DEG = 22.0       # degrees per second (adjust live with LEFT / RIGHT)
START_WITH_TAG = True           # TAB adds / removes the tag at any time
START_YAW_DEG = 35.0            # elegant three-quarter view at start
CAMERA_ELEVATION_DEG = 14.0
CAMERA_FOV_DEG = 30.0
FILL_FRACTION = 0.70            # bouquet height as a fraction of the window
FILL_FRACTION_W = 0.82          # max bouquet width as a fraction (narrow windows)
MIN_WINDOW = (480, 360)
SHADOW_MAP_SIZE = 2048
STUD_SIDES = 8                  # octagonal "pixel" studs (keep low for voxel look)

# The tag starts with this text; press ENTER in the window to write your own.
TAG_DEFAULT_TEXT = "ENTER A SENTENCE"
TAG_PIXEL = 0.30                # size of one tag pixel (bouquet voxel = 1.0)
TAG_MAX_WIDTH = 15.0            # long lines shrink their pixels to keep the tag tiny
TAG_MAX_CHARS = 40              # longest message
TAG_LINE_CHARS = 16             # longer messages wrap onto up to 3 lines
TAG_MAX_LINES = 3

UI_HIDE_AFTER = 3.0             # control bar fades out after this many idle seconds

RANDOM_SEED = 7

# -----------------------------------------------------------------------------
#  palette  (name: (sRGB colour, studs on exposed tops?))
# -----------------------------------------------------------------------------
PALETTE = {
    # dusty pink rose
    "dp_core": ((150, 62, 82), True), "dp_in": ((186, 92, 108), True),
    "dp_mid": ((208, 124, 134), True), "dp_out": ((222, 146, 152), True),
    "dp_tip": ((238, 180, 182), False),
    # blush pink rose
    "bl_core": ((196, 112, 120), True), "bl_in": ((226, 156, 156), True),
    "bl_mid": ((240, 180, 176), True), "bl_out": ((246, 198, 192), True),
    "bl_tip": ((252, 222, 214), False),
    # deep rose
    "dr_core": ((104, 18, 42), True), "dr_in": ((142, 32, 62), True),
    "dr_mid": ((168, 48, 78), True), "dr_out": ((186, 66, 94), True),
    "dr_tip": ((210, 104, 124), False),
    # cream / ivory flowers
    "cr_pet": ((242, 232, 208), False), "cr_pet2": ((250, 244, 228), False),
    "cr_ctr": ((212, 196, 120), True), "cr_stam": ((168, 150, 80), True),
    # baby's breath
    "white": ((250, 248, 240), True),
    # greens
    "leaf": ((96, 140, 88), True), "leaf_d": ((70, 114, 74), True),
    "leaf_l": ((138, 170, 110), True), "stem": ((84, 126, 76), True),
    "foliage": ((70, 112, 72), True), "foliage2": ((88, 132, 84), True),
    "sepal": ((88, 132, 80), True),
    # wrapping
    "wr_cream": ((236, 224, 204), True), "wr_blush": ((230, 192, 188), True),
    "wr_muted": ((204, 152, 158), True), "wr_lining": ((186, 126, 136), True),
    # ribbon
    "ribbon": ((174, 62, 92), False), "ribbon_d": ((138, 42, 70), False),
    # tag
    "tag_plate": ((248, 242, 230), False), "tag_border": ((226, 176, 180), False),
    "tag_text": ((150, 40, 76), False), "tag_gold": ((212, 172, 96), False),
    "tag_string": ((236, 226, 204), False),
}
PAL_NAMES = list(PALETTE.keys())
PAL_INDEX = {n: i + 1 for i, n in enumerate(PAL_NAMES)}          # 0 = empty
ROSE_COLORS = {
    "dusty": ["dp_core", "dp_in", "dp_mid", "dp_out", "dp_tip"],
    "blush": ["bl_core", "bl_in", "bl_mid", "bl_out", "bl_tip"],
    "deep": ["dr_core", "dr_in", "dr_mid", "dr_out", "dr_tip"],
}

# 5-row pixel font ('#' = raised pixel)
PIXEL_FONT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#"],
    "N": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#...#", "#...#", "#.#.#", "##.##", "#...#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"], "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"], " ": ["..", "..", "..", "..", ".."],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    "-": ["...", "...", "###", "...", "..."], ".": [".", ".", ".", ".", "#"],
    "!": ["#", "#", "#", ".", "#"], "'": ["#", "#", ".", ".", "."],
    ",": ["..", "..", "..", ".#", "#."], "&": [".#.", "#.#", ".#.", "#.#", ".##"],
    "+": ["...", ".#.", "###", ".#.", "..."], "?": ["##.", "..#", ".#.", "...", ".#."],
    "*": [".#.#.", "#####", "#####", ".###.", "..#.."],         # heart
}


def clean_name(text):
    """Upper-case, keep only characters the pixel font can draw."""
    out = "".join(ch for ch in str(text).upper() if ch in PIXEL_FONT)
    out = " ".join(out.split())                     # collapse spaces
    return out[:TAG_MAX_CHARS]


def wrap_text(text):
    """Split a message into at most TAG_MAX_LINES lines of TAG_LINE_CHARS."""
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        while len(w) > TAG_LINE_CHARS:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:TAG_LINE_CHARS])
            w = w[TAG_LINE_CHARS:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= TAG_LINE_CHARS:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur or not lines:
        lines.append(cur)
    return lines[:TAG_MAX_LINES]


# =============================================================================
#  small math helpers
# =============================================================================
def unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float64)


def frame_from_up(up, hint=(0.0, 0.0, 1.0)):
    """Orthonormal frame (columns = local u, v, w) with local v = `up`."""
    v = unit(up)
    h = np.asarray(hint, np.float64)
    if abs(np.dot(h, v)) > 0.95:
        h = np.array([1.0, 0, 0])
    u = unit(np.cross(v, h))
    w = np.cross(u, v)
    return np.column_stack([u, v, w])


def dir_from_angles(polar_deg, az_deg):
    p, a = math.radians(polar_deg), math.radians(az_deg)
    return np.array([math.sin(p) * math.cos(a), math.cos(p), math.sin(p) * math.sin(a)])


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy) / 2)
    m = np.zeros((4, 4), np.float64)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def ortho(l, r, b, t, n, f):
    m = np.eye(4)
    m[0, 0] = 2 / (r - l)
    m[1, 1] = 2 / (t - b)
    m[2, 2] = -2 / (f - n)
    m[0, 3] = -(r + l) / (r - l)
    m[1, 3] = -(t + b) / (t - b)
    m[2, 3] = -(f + n) / (f - n)
    return m


def look_at(eye, target, up=(0, 1, 0)):
    eye = np.asarray(eye, np.float64)
    f = unit(np.asarray(target) - eye)
    s = unit(np.cross(f, up))
    u = np.cross(s, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def mat_bytes(m):
    return np.ascontiguousarray(m.T, dtype="f4").tobytes()


# =============================================================================
#  VOXEL GRID
# =============================================================================
class VoxelGrid:
    """Dense grid of palette indices (0 = empty). Components are 'painted' by
    evaluating an implicit shape in their own (rotated) local frame at every
    voxel centre - so everything lands on one global block grid with crisp,
    stepped edges."""

    def __init__(self, lo, hi, scale=1.0, origin=(0.0, 0.0, 0.0)):
        self.lo = np.array(lo, np.int64)
        self.hi = np.array(hi, np.int64)
        self.scale = scale
        self.origin = np.array(origin, np.float64)
        self.data = np.zeros(tuple(self.hi - self.lo), np.uint8)

    def paint_world(self, lo, hi, fn, only_empty=False):
        """Paint with fn(x, y, z) evaluated in absolute coordinates over a box."""
        lo = np.asarray(lo, np.float64)
        hi = np.asarray(hi, np.float64)
        c = (lo + hi) / 2
        r = float(np.max(hi - lo) / 2)
        self.paint(c, np.eye(3), r,
                   lambda u, v, w: fn(u + c[0], v + c[1], w + c[2]), only_empty)

    def paint(self, center, R, radius, fn, only_empty=False):
        """fn(u, v, w) -> palette index array (0 = keep). R columns = local axes."""
        c = np.asarray(center, np.float64)
        lo = np.maximum(np.floor(c - radius).astype(np.int64), self.lo)
        hi = np.minimum(np.ceil(c + radius).astype(np.int64) + 1, self.hi)
        if np.any(hi <= lo):
            return
        ax = [np.arange(lo[i], hi[i]) + 0.5 for i in range(3)]
        X, Y, Z = np.meshgrid(*ax, indexing="ij")
        P = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
        L = P @ np.asarray(R, np.float64)
        col = fn(L[..., 0], L[..., 1], L[..., 2])
        sl = tuple(slice(lo[i] - self.lo[i], hi[i] - self.lo[i]) for i in range(3))
        dst = self.data[sl]
        m = col > 0
        if only_empty:
            m &= dst == 0
        dst[m] = col[m]

    def set_points(self, pts, color):
        pts = np.floor(np.asarray(pts)).astype(np.int64) - self.lo
        ok = np.all((pts >= 0) & (pts < self.data.shape), axis=1)
        pts = pts[ok]
        self.data[pts[:, 0], pts[:, 1], pts[:, 2]] = PAL_INDEX[color]


def pick(cond_list, default=0):
    """np.select helper returning uint8 palette indices."""
    conds = [c for c, _ in cond_list]
    vals = [PAL_INDEX[n] if isinstance(n, str) else n for _, n in cond_list]
    return np.select(conds, vals, default).astype(np.uint8)


# =============================================================================
#  BOUQUET COMPONENTS
# =============================================================================
def rose_fn(s, colors, twist):
    """LEGO rose: a centre bud + four rings of stepped, flaring petals with a
    voxel gap between neighbouring petals, a scalloped (stepped) rim and a
    five-pointed green sepal star underneath."""
    core, c_in, c_mid, c_out, c_tip = colors
    #          a     b     curl  v0    top   n  colour  tip-colour
    layers = [(2.1, 0.18, 0.00, 0.0, 4.6, 3, c_in, c_mid),
              (3.1, 0.30, 0.02, -0.4, 4.1, 4, c_mid, c_out),
              (4.1, 0.44, 0.05, -1.0, 3.3, 5, c_out, c_tip),
              (5.1, 0.62, 0.09, -1.8, 2.1, 5, c_out, c_tip)]

    def fn(u, v, w):
        r = np.sqrt(u * u + w * w)
        th = np.arctan2(w, u)
        out = np.zeros(u.shape, np.uint8)
        vs = v / s
        # five-pointed sepal star + receptacle
        star = 2.0 + 4.6 * np.clip(np.cos(5 * (th + twist)), 0, 1) ** 3
        sep = (vs > -2.7) & (vs < -1.7) & (r < star * s)
        rec = (vs > -3.6) & (vs <= -1.7) & (r < 2.2 * s)
        out[sep | rec] = PAL_INDEX["sepal"]
        # tight spiral centre
        spiral_r = (1.0 + 0.55 * ((th + twist) % (2 * np.pi)) / (2 * np.pi)) * s
        cen = ((r < 1.0 * s) & (vs > -1.7) & (vs < 4.4)) | \
              ((np.abs(r - spiral_r) < 0.6) & (vs > -1.7) & (vs < 5.0))
        out[cen] = PAL_INDEX[core]
        for li, (a, b, curl, v0, top, n, col, tipc) in enumerate(layers):
            h = np.clip(vs - v0, 0, None)
            R = (a + b * h + curl * h * h) * s
            shell = np.abs(r - R) < 0.62
            seg = 2 * np.pi / n
            ph = ((th + twist * (li + 1) * 1.7) % seg) / seg
            ptop = top - 1.6 * (2 * ph - 1) ** 2
            gapw = 0.55 / np.maximum(R, 0.5) / seg
            in_gap = (np.minimum(ph, 1 - ph) < gapw) & (vs > v0 + 1.2)
            m = shell & (vs >= v0 - 0.2) & (vs <= ptop) & ~in_gap
            tip = m & (vs > ptop - 0.9)
            out[m & (out == 0)] = PAL_INDEX[col]
            out[tip & (out == PAL_INDEX[col])] = PAL_INDEX[tipc]
        return out
    return fn, 9.0 * s


def cream_flower_fn(s, twist):
    """Ivory flower: two rings of broad cupped petals around a studded centre."""
    def fn(u, v, w):
        r = np.sqrt(u * u + w * w)
        th = np.arctan2(w, u)
        out = np.zeros(u.shape, np.uint8)
        for (n, rmax, rmid, half, cup, lift, col, off) in (
                (6, 6.4, 3.5, 2.5, 0.075, 0.0, "cr_pet", 0.0),
                (5, 4.2, 2.4, 1.8, 0.16, 0.8, "cr_pet2", 0.6)):
            seg = 2 * np.pi / n
            d = ((th + twist + off) % seg) - seg / 2
            perp = r * np.abs(np.sin(d))
            along = r * np.cos(d)
            ell = 1 - ((along - rmid * s) / ((rmax - 0.5) * s / 2 + 0.6)) ** 2
            hw = half * s * np.sqrt(np.clip(ell, 0, 1))
            surf = lift * s + cup * r * r / s
            m = (perp < hw) & (np.abs(v - surf) < 0.62) & (along > 0)
            out[m] = PAL_INDEX[col]
        ctr = (r < 1.7 * s) & (v > -0.3) & (v < 1.9 * s)
        stam = (r >= 1.7 * s) & (r < 2.4 * s) & (v > 0.4) & (v < 1.6 * s)
        out[stam] = PAL_INDEX["cr_stam"]
        out[ctr] = PAL_INDEX["cr_ctr"]
        rec = (v < 0) & (v > -1.8) & (r < 1.7 * s)
        out[rec & (out == 0)] = PAL_INDEX["sepal"]
        return out
    return fn, 8.0 * s


def bud_fn(s, colors):
    def fn(u, v, w):
        r = np.sqrt(u * u + w * w)
        th = np.arctan2(w, u)
        out = np.zeros(u.shape, np.uint8)
        body = (r / (2.3 * s)) ** 2 + ((v - 2.8 * s) / (3.6 * s)) ** 2 < 1
        out[body] = PAL_INDEX[colors[2]]
        out[body & (v > 4.6 * s)] = PAL_INDEX[colors[3]]
        spiral = body & (np.abs(((th * 2 + v * 0.7) % 3.0) - 1.5) < 0.25)
        out[spiral] = PAL_INDEX[colors[1]]
        sep = (v > -0.6) & (v < 1.6 * s) & \
              (r < (1.6 + 1.6 * np.clip(np.cos(3 * th), 0, 1) ** 2) * s) & \
              (r > (1.6 + 1.6 * np.clip(np.cos(3 * th), 0, 1) ** 2) * s - 1.25)
        out[sep] = PAL_INDEX["sepal"]
        out[(v > -2.5) & (v <= 0) & (r < 1.1)] = PAL_INDEX["stem"]
        return out
    return fn, 7.0 * s


def leaf_fn(length, width, curl):
    """Stepped LEGO leaf (u = length, v = normal, w = side) with a midrib."""
    def fn(u, v, w):
        out = np.zeros(u.shape, np.uint8)
        t = np.clip(u / length, 0, 1)
        hw = width * np.sin(np.pi * t) ** 0.75
        vc = curl * t * t * length
        m = (u > 0) & (u < length) & (np.abs(w) < hw) & (np.abs(v - vc) < 0.62)
        out[m] = PAL_INDEX["leaf"]
        out[m & (np.abs(w) > hw - 1.0) & (np.abs(w) > 1.0)] = PAL_INDEX["leaf_l"]
        out[m & (np.abs(w) < 0.65)] = PAL_INDEX["leaf_d"]
        return out
    return fn, length + 2


def capsule_fn(a, b, radius, color):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    d = b - a
    L2 = max(float(d @ d), 1e-9)

    def fn(x, y, z):          # identity frame centred at a
        t = np.clip((x * d[0] + y * d[1] + z * d[2]) / L2, 0, 1)
        px, py, pz = x - t * d[0], y - t * d[1], z - t * d[2]
        m = px * px + py * py + pz * pz < radius * radius
        return np.where(m, PAL_INDEX[color], 0).astype(np.uint8)
    return fn, math.sqrt(L2) + radius + 1


# -----------------------------------------------------------------------------
WRAP_Y0, WRAP_Y1 = 6.0, 37.0


def wrap_r(y):
    t = np.clip(np.asarray(y, np.float64) - WRAP_Y0, 0, None)
    return 3.0 + t * 0.34 + 0.0068 * t * t        # slim cone with a soft tulip flare


N_SHEETS = 6
SHEET_HW = math.radians(54)


def wrapper_fn():
    """Folded, layered paper wrap: an inner lining cone + six overlapping
    pleated sheets with pointed, stepped tips; widest at the top."""
    def fn(x, y, z):
        out = np.zeros(x.shape, np.uint8)
        rho = np.sqrt(x * x + z * z)
        th = np.arctan2(z, x)
        rb = wrap_r(y)
        lining = (np.abs(rho - rb) < 0.7) & (y > WRAP_Y0) & (y < WRAP_Y1 + 2)
        out[lining] = PAL_INDEX["wr_lining"]
        for i in range(N_SHEETS):
            c = math.radians(15 + i * 360 / N_SHEETS)
            d = np.angle(np.exp(1j * (th - c)))
            k = np.clip(1 - np.abs(d) / SHEET_HW, 0, 1)
            layer = 0.9 if i % 2 else 1.7
            fold = 0.45 * k + 0.25 * np.abs(np.sin(d * 3.0))     # soft pleats
            R = rb + layer + fold
            top = WRAP_Y1 - 1 + 8.0 * k ** 1.3 + (1.5 if i % 2 else 0)
            m = (k > 0) & (np.abs(rho - R) < 0.72) & (y > WRAP_Y0) & (y < top)
            col = ("wr_cream", "wr_blush", "wr_muted")[i % 3]
            out[m] = PAL_INDEX[col]
        return out
    return fn


RIB_Y = 13.0


def ribbon_geometry():
    rb = wrap_r(RIB_Y + 1.5) + 3.1
    knot = np.array([0.0, RIB_Y + 1.5, rb + 1.0])
    return rb, knot


def ribbon_fn():
    rb_mid, knot = ribbon_geometry()

    def fn(x, y, z):
        out = np.zeros(x.shape, np.uint8)
        rho = np.sqrt(x * x + z * z)
        rr = wrap_r(y) + 3.1
        band = (np.abs(rho - rr) < 0.75) & (y > RIB_Y) & (y < RIB_Y + 4)
        out[band] = PAL_INDEX["ribbon"]
        kx, ky, kz = knot
        # knot
        kn = (np.abs(x) < 2.2) & (np.abs(y - ky) < 2.2) & (np.abs(z - kz) < 1.3)
        out[kn] = PAL_INDEX["ribbon_d"]
        # two stepped loops
        for sd in (-1, 1):
            cx, cy = kx + sd * 6.4, ky + 2.0
            e = ((x - cx) / 6.0) ** 2 + ((y - cy) / 3.8) ** 2
            zc = kz - 0.3 - 0.28 * np.abs(x - kx)
            loop = (e > 0.42) & (e < 1.0) & (np.abs(z - zc) < 1.4) & (sd * (x - kx) > 1.2)
            out[loop] = PAL_INDEX["ribbon"]
            # tails with a V-notch
            a = np.array([kx + sd * 1.2, ky - 1.5, kz])
            b = np.array([kx + sd * 5.0, 4.5, wrap_r(6) + 2.6])
            d = b - a
            L = np.linalg.norm(d)
            dn = d / L
            px, py, pz = x - a[0], y - a[1], z - a[2]
            t = (px * dn[0] + py * dn[1] + pz * dn[2]) / L
            perp_xy = np.abs(px * dn[1] - py * dn[0])
            qx, qy, qz = px - t * L * dn[0], py - t * L * dn[1], pz - t * L * dn[2]
            dz = np.abs(qz)
            notch = (t > 0.86) & (perp_xy < (t - 0.86) / 0.14 * 1.6)
            tail = (t > 0) & (t < 1) & (perp_xy < 1.6) & (dz < 0.7) & ~notch
            out[tail] = PAL_INDEX["ribbon"]
        return out
    return fn, knot


# -----------------------------------------------------------------------------
DOME_C = np.array([0.0, 49.0, 0.0])
DOME_R = 24.0
GATHER = np.array([0.0, 20.0, 0.0])


def build_bouquet():
    g = VoxelGrid((-42, -2, -42), (42, 106, 42))
    I = np.eye(3)
    rng = np.random.default_rng(RANDOM_SEED)

    # --- foliage core (dark green blocks) - hides the stems inside the dome
    def foliage(x, y, z):
        d = np.sqrt(x * x + y * y + z * z)
        m = (d < 18.0) & (y > -16)
        n = (np.floor(x / 2) + np.floor(y / 2) * 3 + np.floor(z / 2) * 7) % 3
        return np.where(m, np.where(n == 0, PAL_INDEX["foliage2"], PAL_INDEX["foliage"]),
                        0).astype(np.uint8)
    g.paint(DOME_C, I, 19, foliage)

    # --- wrapper (painted before flowers; flowers overwrite where they touch)
    g.paint_world((-42, -2, -42), (42, 80, 42), wrapper_fn())

    # --- stems out of the bottom
    for k in range(7):
        a = 2 * math.pi * k / 7
        p = np.array([1.8 * math.cos(a), 0, 1.8 * math.sin(a)]) if k < 6 else np.zeros(3)
        fn, rad = capsule_fn((0, 0, 0), (p[0] * 0.3, 30, p[2] * 0.3), 1.05, "stem")
        g.paint(p + np.array([0, -1.5, 0]), I, rad, fn, only_empty=True)

    heads = []           # (position, axis) for stems

    # --- roses
    roses = [(0, 0, 1.2, "dusty")]
    for i, pal in enumerate(["deep", "blush", "dusty", "deep", "blush"]):
        roses.append((33, 0 + i * 72, 1.02, pal))
    for i, pal in enumerate(["blush", "dusty", "deep", "blush", "dusty", "deep"]):
        roses.append((68, 30 + i * 60, 1.05, pal))
    for i, (polar, az, sc, pal) in enumerate(roses):
        axis = dir_from_angles(polar, az)
        pos = DOME_C + axis * DOME_R
        R = frame_from_up(axis) @ np.array(
            [[math.cos(i), 0, math.sin(i)], [0, 1, 0], [-math.sin(i), 0, math.cos(i)]])
        fn, rad = rose_fn(sc, ROSE_COLORS[pal], twist=i * 0.9)
        g.paint(pos, R, rad, fn)
        heads.append((pos - axis * 3.5 * sc, axis))

    # --- ivory flowers between the two rose rings
    for i in range(5):
        axis = dir_from_angles(54, 36 + i * 72)
        pos = DOME_C + axis * (DOME_R + 0.5)
        fn, rad = cream_flower_fn(1.0, twist=i * 0.5)
        g.paint(pos, frame_from_up(axis), rad, fn)
        heads.append((pos - axis * 1.5, axis))
    for i in range(3):
        axis = dir_from_angles(90, 0 + i * 120 + 60)
        pos = DOME_C + axis * (DOME_R - 1.0)
        fn, rad = cream_flower_fn(0.8, twist=i)
        g.paint(pos, frame_from_up(axis), rad, fn)

    # --- small spray roses filling the middle band
    for i, pal in enumerate(["blush", "deep", "dusty", "blush", "deep"]):
        axis = dir_from_angles(51, 0 + i * 72)
        pos = DOME_C + axis * (DOME_R - 0.5)
        fn, rad = rose_fn(0.72, ROSE_COLORS[pal], twist=i * 1.1)
        g.paint(pos, frame_from_up(axis) @ rot_y(i * 0.8), rad, fn)
        heads.append((pos - axis * 2.5, axis))

    # --- lower ring just above the wrapper rim: smaller roses + ivory blooms
    low_pals = ["deep", "blush", "dusty", "deep", "blush", "dusty"]
    for i in range(12):
        az = 15 + i * 30
        axis = dir_from_angles(94 + (i % 2) * 4, az)
        if i % 2 == 0:
            pos = DOME_C + axis * (DOME_R - 1.5)
            R = frame_from_up(axis) @ rot_y(i * 1.3)
            fn, rad = rose_fn(0.78, ROSE_COLORS[low_pals[(i // 2) % 6]], twist=i * 0.7)
            g.paint(pos, R, rad, fn)
        else:
            pos = DOME_C + axis * (DOME_R - 2.0)
            fn, rad = cream_flower_fn(0.78, twist=i * 0.4)
            g.paint(pos, frame_from_up(axis), rad, fn)
        heads.append((pos - axis * 2.5, axis))

    # --- buds rising above the dome
    for i, pal in enumerate(["blush", "dusty", "deep", "blush"]):
        axis = dir_from_angles(23, 36 + i * 90)
        pos = DOME_C + axis * (DOME_R + 5.5)
        fn, rad = bud_fn(0.85, ROSE_COLORS[pal])
        g.paint(pos, frame_from_up(axis), rad, fn)
        heads.append((pos, axis))

    # --- baby's breath sprigs (single white blocks on tiny stems)
    for i in range(10):
        axis = dir_from_angles(78 + (i % 2) * 10, 6 + i * 36)
        base = DOME_C + axis * (DOME_R + 1.5)
        pts = []
        for _ in range(16):
            v = unit(rng.normal(size=3) + axis * 1.6)
            pts.append(base + v * rng.uniform(0.5, 3.2))
        g.set_points(np.array(pts), "white")

    # --- stems from every head to the gathering point (hidden in foliage/wrap)
    for pos, axis in heads:
        fn, rad = capsule_fn((0, 0, 0), GATHER - pos, 1.0, "stem")
        g.paint(pos, I, rad, fn, only_empty=True)

    # --- leaves: a collar around the rim + some between flowers
    for k in range(12):
        az = math.radians(k * 30 + 8)
        out = np.array([math.cos(az), 0, math.sin(az)])
        side = np.array([-math.sin(az), 0, math.cos(az)])
        u = unit(out * 0.92 + np.array([0, 0.30, 0]))
        nrm = unit(np.cross(side, u))
        if nrm[1] < 0:
            nrm = -nrm
        R = np.column_stack([u, nrm, side])
        base = np.array([0, WRAP_Y1 + 5, 0]) + out * 15.0
        fn, rad = leaf_fn(13 if k % 2 else 11, 3.7, -0.22)
        g.paint(base, R, rad, fn, only_empty=True)
    for k in range(11):
        az = math.radians(k * 60 if k < 6 else 54 + (k - 6) * 72)
        axis = dir_from_angles(62, k * 60 + 2) if k < 6 else dir_from_angles(42, 54 + (k - 6) * 72)
        side = np.array([-math.sin(az), 0, math.cos(az)])
        u = unit(axis + np.array([0, 0.3, 0]))
        nrm = unit(np.cross(side, u))
        if nrm[1] < 0:
            nrm = -nrm
        R = np.column_stack([u, nrm, side])
        fn, rad = leaf_fn(9, 2.8, -0.18)
        g.paint(DOME_C + axis * (DOME_R - 3), R, rad, fn, only_empty=True)

    # --- ribbon + bow (on top of everything)
    fn, knot = ribbon_fn()
    g.paint_world((-42, -2, -42), (42, 60, 42), fn)
    return g, knot


# -----------------------------------------------------------------------------
def build_tag(knot, text):
    """Tiny micro-block gift tag: cream plate with a blush frame, raised
    pixel-font lettering, a gold eyelet and a thin string tied to the knot.
    The plate is sized to the name; long names use smaller pixels."""
    text = clean_name(text) or " "
    lines = wrap_text(text)
    line_glyphs = [[PIXEL_FONT[ch] for ch in ln] or [PIXEL_FONT[" "]] for ln in lines]
    line_w = [sum(len(g[0]) for g in gl) + len(gl) - 1 for gl in line_glyphs]
    text_w = max(line_w)
    n_lines = len(lines)
    text_h = 5 * n_lines + 2 * (n_lines - 1)
    pad = 2
    W = max(text_w + 2 * pad + 2, 11)
    H = text_h + 2 * pad + 2
    px = min(TAG_PIXEL, TAG_MAX_WIDTH / W)
    # tag placement in bouquet space (front = +z): hangs below the bow knot
    top_y = knot[1] - 6.8
    zc = knot[2] + 1.6
    ox = -W * px / 2
    oy = top_y - H * px
    oz = zc
    lo_y = int(math.floor((oy - 0.5) / px))
    # grid in tag-pixel units, origin chosen so index * px = world position
    gx0 = int(math.floor(ox / px)) - 2
    gy0 = lo_y - 2
    gz0 = int(math.floor(oz / px)) - 3
    span_y = int(math.ceil((knot[1] - oy) / px)) + 8
    t = VoxelGrid((gx0, gy0, gz0), (gx0 + W + 6, gy0 + span_y, gz0 + 10), scale=px)

    def put(ix, iy, iz, color):
        a = np.array([[ix, iy, iz]], np.float64) + 0.5
        t.set_points(a, color)

    bx = int(math.floor(ox / px))
    by = int(math.floor(oy / px))
    bz = int(math.floor(oz / px))
    # plate (2 pixels thick) with stepped corners
    for i in range(W):
        for j in range(H):
            corner = (i in (0, W - 1)) and (j in (0, H - 1))
            if corner:
                continue
            frame = i in (0, 1, W - 2, W - 1) or j in (0, 1, H - 2, H - 1)
            frame = frame and not ((i in (1, W - 2)) and (j in (1, H - 2)))
            for k in (0, 1):
                put(bx + i, by + j, bz + k, "tag_border" if frame else "tag_plate")
            if frame:                                  # raised frame
                put(bx + i, by + j, bz + 2, "tag_border")
    # raised lettering (front = +z), every line centred on the plate
    for li, (gl_line, lw) in enumerate(zip(line_glyphs, line_w)):
        cx = bx + (W - lw) // 2
        base_y = by + pad + 1 + (n_lines - 1 - li) * 7
        for gl in gl_line:
            for r, row in enumerate(gl):
                for c, ch in enumerate(row):
                    if ch == "#":
                        put(cx + c, base_y + (4 - r), bz + 2, "tag_text")
            cx += len(gl[0]) + 1
    # gold eyelet above the top edge
    ex = bx + W // 2
    for (dx, dy) in ((-1, 0), (1, 0), (-1, 1), (1, 1), (0, 2), (-1, 2), (1, 2), (0, -0)):
        if (dx, dy) != (0, 0):
            put(ex + dx, by + H + dy, bz + 1, "tag_gold")
    put(ex, by + H, bz + 1, "tag_gold")
    # thin string from the eyelet up to the knot (1-pixel line)
    a = np.array([ex + 0.5, by + H + 2.5, bz + 1.5])
    b = np.array([knot[0] / px, (knot[1] - 1.6) / px, (knot[2] + 1.0) / px])
    n = int(np.linalg.norm(b - a) * 2) + 2
    pts = a + (b - a) * np.linspace(0, 1, n)[:, None]
    t.set_points(pts, "tag_string")
    center = np.array([0.0, oy + H * px / 2, zc + px])
    pivot = b * px                                   # where the string meets the knot
    return t, center, px, text, pivot, (W * px, H * px)


# =============================================================================
#  MESHING: exposed faces + vertex ambient occlusion + brick seams + studs
# =============================================================================
def palette_arrays():
    lin = np.zeros((len(PAL_NAMES) + 1, 3), np.float32)
    stud = np.zeros(len(PAL_NAMES) + 1, bool)
    for n, i in PAL_INDEX.items():
        c, st = PALETTE[n]
        lin[i] = (np.array(c, np.float32) / 255.0) ** 2.2
        stud[i] = st
    return lin, stud


def mesh_grid(grid, allow_studs=True, seed=1):
    """Returns (vertices[N,16] float32, indices uint32, stud instances[M,6])."""
    lin, stud_ok = palette_arrays()
    D = np.pad(grid.data, 2)
    O = D > 0
    rng = np.random.default_rng(seed)
    # brick ids: pair neighbouring same-colour voxels into 1x2 bricks,
    # alternating direction per layer (running-bond look)
    nx, ny, nz = D.shape
    ids = np.arange(D.size, dtype=np.int64).reshape(D.shape)
    yy = np.arange(ny)[None, :, None]
    xx = np.arange(nx)[:, None, None]
    zz = np.arange(nz)[None, None, :]
    same_x = np.zeros_like(O)
    same_x[:-1] = O[:-1] & (D[:-1] == D[1:])
    pair_x = same_x & (xx % 2 == 0) & (yy % 2 == 0)
    ids[1:][pair_x[:-1]] = ids[:-1][pair_x[:-1]]
    same_z = np.zeros_like(O)
    same_z[:, :, :-1] = O[:, :, :-1] & (D[:, :, :-1] == D[:, :, 1:])
    pair_z = same_z & (zz % 2 == 0) & (yy % 2 == 1)
    ids[:, :, 1:][pair_z[:, :, :-1]] = ids[:, :, :-1][pair_z[:, :, :-1]]
    ids[~O] = -1
    jitter = rng.uniform(0.93, 1.05, D.size).astype(np.float32)

    verts, inds, base = [], [], 0
    studs = []
    s = grid.scale
    off = grid.lo.astype(np.float64) - 2
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        for sg in (-1, 1):
            e = np.zeros(3, int)
            e[a] = sg
            nb = np.roll(O, -sg, axis=a)
            face = O & ~nb
            I = np.array(np.nonzero(face)).T            # padded cell coords
            if len(I) == 0:
                continue
            L = I + e                                    # empty neighbour layer
            eb = np.zeros(3, int); eb[b] = 1
            ec = np.zeros(3, int); ec[c] = 1

            def occ(P):
                return O[P[:, 0], P[:, 1], P[:, 2]].astype(np.int32)

            corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
            pos, ao = [], []
            for cb, cc in corners:
                ob, oc = 2 * cb - 1, 2 * cc - 1
                s1 = occ(L + ob * eb)
                s2 = occ(L + oc * ec)
                cr = occ(L + ob * eb + oc * ec)
                aov = np.where((s1 + s2) == 2, 0, 3 - (s1 + s2 + cr))
                ao.append(aov / 3.0)
                p = I.astype(np.float64) + (1 if sg > 0 else 0) * np.eye(3)[a] \
                    + cb * np.eye(3)[b] + cc * np.eye(3)[c]
                pos.append((p + off) * s + grid.origin)
            cid = ids[I[:, 0], I[:, 1], I[:, 2]]
            seams = []
            for dd in (-eb, eb, -ec, ec):
                P = I + dd
                seams.append((ids[P[:, 0], P[:, 1], P[:, 2]] != cid).astype(np.float32))
            col = lin[D[I[:, 0], I[:, 1], I[:, 2]]] * \
                jitter[np.clip(cid, 0, None)][:, None]
            nrm = np.zeros((len(I), 3), np.float32)
            nrm[:, a] = sg
            n = len(I)
            V = np.zeros((n, 4, 16), np.float32)
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            for k in range(4):
                V[:, k, 0:3] = pos[k]
                V[:, k, 3:6] = nrm
                V[:, k, 6:9] = col
                V[:, k, 9] = ao[k]
                V[:, k, 10:12] = uvs[k]
                V[:, k, 12] = seams[0]
                V[:, k, 13] = seams[1]
                V[:, k, 14] = seams[2]
                V[:, k, 15] = seams[3]
            q = base + np.arange(n)[:, None] * 4
            flip = (ao[0] + ao[2]) < (ao[1] + ao[3])
            t1 = np.where(flip[:, None], np.array([1, 2, 3]), np.array([0, 1, 2]))
            t2 = np.where(flip[:, None], np.array([1, 3, 0]), np.array([0, 2, 3]))
            inds.append(np.concatenate([q + t1, q + t2], 1).reshape(-1))
            verts.append(V.reshape(-1, 16))
            base += n * 4
            if allow_studs and a == 1 and sg == 1:
                ok = stud_ok[D[I[:, 0], I[:, 1], I[:, 2]]]
                if ok.any():
                    J = I[ok]
                    sp = ((J + np.array([0.5, 1.0, 0.5]) + off) * s) + grid.origin
                    studs.append(np.concatenate([sp, col[ok]], 1))
    V = np.concatenate(verts).astype(np.float32)
    Idx = np.concatenate(inds).astype(np.uint32)
    St = np.concatenate(studs).astype(np.float32) if studs else np.zeros((0, 6), np.float32)
    return V, Idx, St


def stud_mesh(radius=0.30, height=0.20, sides=STUD_SIDES):
    """Low-poly (octagonal) LEGO stud: side quads + flat top. pos(3) nrm(3)"""
    v = []
    for i in range(sides):
        a0 = 2 * math.pi * (i + 0.5) / sides
        a1 = 2 * math.pi * (i + 1.5) / sides
        am = (a0 + a1) / 2
        n = (math.cos(am), 0.0, math.sin(am))
        p00 = (radius * math.cos(a0), 0.0, radius * math.sin(a0))
        p01 = (radius * math.cos(a1), 0.0, radius * math.sin(a1))
        p10 = (p00[0], height, p00[2])
        p11 = (p01[0], height, p01[2])
        for p in (p00, p01, p11, p00, p11, p10):
            v.append(p + n)
        v.append((0.0, height, 0.0, 0, 1, 0))
        v.append(p10 + (0, 1, 0))
        v.append(p11 + (0, 1, 0))
    return np.array(v, np.float32)


# =============================================================================
#  SHADERS
# =============================================================================
COMMON_FS = """
uniform vec3 u_cam;
uniform vec3 u_key_dir;
uniform vec3 u_fill_dir;
uniform vec3 u_rim_dir;
uniform sampler2DShadow u_shadow;
uniform int u_use_shadow;
uniform float u_shadow_texel;

float shadow_at(vec4 lp) {
    if (u_use_shadow == 0) return 1.0;
    vec3 p = lp.xyz / lp.w * 0.5 + 0.5;
    if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0 || p.z > 1.0) return 1.0;
    float s = 0.0;
    for (int x = -2; x <= 2; x++)
        for (int y = -2; y <= 2; y++)
            s += texture(u_shadow, vec3(p.xy + vec2(x, y) * u_shadow_texel, p.z - 0.0015));
    return s / 25.0;
}

vec3 aces(vec3 x) {
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}

vec3 plastic(vec3 albedo, vec3 N, vec3 P, float ao, float sh) {
    vec3 V = normalize(u_cam - P);
    vec3 L = normalize(u_key_dir);
    vec3 H = normalize(L + V);
    float nl = max(dot(N, L), 0.0);
    float ndv = max(dot(N, V), 0.0);
    // soft studio lighting
    vec3 key = vec3(1.00, 0.96, 0.92) * 2.3 * nl * sh;
    vec3 fill = vec3(0.86, 0.88, 1.0) * 0.55 * max(dot(N, normalize(u_fill_dir)), 0.0);
    vec3 rimc = vec3(1.0, 0.72, 0.80) * 0.9 * max(dot(N, normalize(u_rim_dir)), 0.0)
                * pow(1.0 - ndv, 1.6);
    float hemi = N.y * 0.5 + 0.5;
    vec3 amb = mix(vec3(0.07, 0.05, 0.06), vec3(0.30, 0.28, 0.30), hemi);
    float aoT = mix(0.28, 1.0, ao);
    vec3 col = albedo * ((key + fill) * mix(0.55, 1.0, aoT) + amb * aoT) + albedo * rimc;
    // glossy plastic: sharp highlight + broad sheen + studio softbox reflection
    float fres = 0.04 + 0.96 * pow(1.0 - ndv, 5.0);
    float spec = pow(max(dot(N, H), 0.0), 90.0) * 1.6 + pow(max(dot(N, H), 0.0), 18.0) * 0.12;
    col += vec3(1.0, 0.97, 0.94) * spec * sh * mix(0.6, 1.0, aoT);
    vec3 R = reflect(-V, N);
    float box = smoothstep(0.35, 0.75, R.y) * smoothstep(1.0, 0.2, abs(R.x + 0.3));
    col += vec3(0.9, 0.86, 0.88) * box * fres * 0.9 * aoT;
    return col;
}
"""

MESH_VS = """
#version 330
in vec3 in_pos; in vec3 in_nrm; in vec3 in_col; in float in_ao; in vec2 in_uv; in vec4 in_seam;
uniform mat4 u_model; uniform mat4 u_vp; uniform mat4 u_light;
out vec3 v_pos; out vec3 v_nrm; out vec3 v_col; out float v_ao; out vec2 v_uv;
out vec4 v_seam; out vec4 v_lp;
void main() {
    vec4 wp = u_model * vec4(in_pos, 1.0);
    vec3 n = mat3(u_model) * in_nrm;
    v_pos = wp.xyz; v_nrm = n; v_col = in_col; v_ao = in_ao; v_uv = in_uv; v_seam = in_seam;
    v_lp = u_light * vec4(wp.xyz + n * 0.12, 1.0);
    gl_Position = u_vp * wp;
}
"""

MESH_FS = """
#version 330
in vec3 v_pos; in vec3 v_nrm; in vec3 v_col; in float v_ao; in vec2 v_uv;
in vec4 v_seam; in vec4 v_lp;
out vec4 f_color;
""" + COMMON_FS + """
void main() {
    vec3 N = normalize(v_nrm);
    // brick seams + bevel (only on edges that separate different bricks)
    float d = 1.0;
    if (v_seam.x > 0.5) d = min(d, v_uv.x);
    if (v_seam.y > 0.5) d = min(d, 1.0 - v_uv.x);
    if (v_seam.z > 0.5) d = min(d, v_uv.y);
    if (v_seam.w > 0.5) d = min(d, 1.0 - v_uv.y);
    float seam = 1.0 - smoothstep(0.018, 0.05, d);
    float bevel = smoothstep(0.05, 0.075, d) * (1.0 - smoothstep(0.075, 0.13, d));
    float sh = shadow_at(v_lp);
    vec3 c = plastic(v_col, N, v_pos, v_ao, sh);
    c *= 1.0 - 0.62 * seam;
    c += v_col * bevel * 0.10;
    c = aces(c * 0.95);
    f_color = vec4(pow(c, vec3(1.0 / 2.2)), 1.0);
}
"""

STUD_VS = """
#version 330
in vec3 in_pos; in vec3 in_nrm; in vec3 in_ipos; in vec3 in_icol;
uniform mat4 u_model; uniform mat4 u_vp; uniform mat4 u_light; uniform float u_scale;
out vec3 v_pos; out vec3 v_nrm; out vec3 v_col; out float v_h; out vec4 v_lp;
void main() {
    vec4 wp = u_model * vec4(in_ipos + in_pos * u_scale, 1.0);
    vec3 n = mat3(u_model) * in_nrm;
    v_pos = wp.xyz; v_nrm = n; v_col = in_icol; v_h = in_pos.y / 0.2;
    v_lp = u_light * vec4(wp.xyz + n * 0.06, 1.0);
    gl_Position = u_vp * wp;
}
"""

STUD_FS = """
#version 330
in vec3 v_pos; in vec3 v_nrm; in vec3 v_col; in float v_h; in vec4 v_lp;
out vec4 f_color;
""" + COMMON_FS + """
void main() {
    vec3 N = normalize(v_nrm);
    float sh = shadow_at(v_lp);
    float ao = mix(0.55, 1.0, clamp(v_h * 1.4, 0.0, 1.0));
    vec3 c = plastic(v_col, N, v_pos, ao, sh);
    c = aces(c * 0.95);
    f_color = vec4(pow(c, vec3(1.0 / 2.2)), 1.0);
}
"""

DEPTH_VS = """
#version 330
in vec3 in_pos;
uniform mat4 u_model; uniform mat4 u_light;
void main() { gl_Position = u_light * u_model * vec4(in_pos, 1.0); }
"""
DEPTH_STUD_VS = """
#version 330
in vec3 in_pos; in vec3 in_ipos;
uniform mat4 u_model; uniform mat4 u_light; uniform float u_scale;
void main() { gl_Position = u_light * u_model * vec4(in_ipos + in_pos * u_scale, 1.0); }
"""
DEPTH_FS = """
#version 330
void main() {}
"""

HUD_VS = """
#version 330
in vec2 in_pos; uniform vec4 u_rect; out vec2 v_uv;
void main() { v_uv = in_pos; gl_Position = vec4(mix(u_rect.xy, u_rect.zw, in_pos), 0.0, 1.0); }
"""
HUD_FS = """
#version 330
in vec2 v_uv; uniform sampler2D u_tex; uniform float u_alpha; out vec4 f_color;
void main() { vec4 c = texture(u_tex, v_uv); f_color = vec4(c.rgb, c.a * u_alpha); }
"""


# =============================================================================
#  RENDERER
# =============================================================================
class Renderer:
    def __init__(self, ctx, scene):
        import moderngl
        self.mgl = moderngl
        self.ctx = ctx
        self.scene = scene
        self.prog_mesh = ctx.program(vertex_shader=MESH_VS, fragment_shader=MESH_FS)
        self.prog_stud = ctx.program(vertex_shader=STUD_VS, fragment_shader=STUD_FS)
        self.prog_depth = ctx.program(vertex_shader=DEPTH_VS, fragment_shader=DEPTH_FS)
        self.prog_dstud = ctx.program(vertex_shader=DEPTH_STUD_VS, fragment_shader=DEPTH_FS)
        self.stud_vbo = ctx.buffer(stud_mesh().tobytes())
        self.parts = {}
        for name, data in scene["parts"].items():
            self.set_part(name, data)
        self.n_stud_verts = len(stud_mesh())
        self.shadow_tex = ctx.depth_texture((SHADOW_MAP_SIZE, SHADOW_MAP_SIZE))
        self.shadow_tex.compare_func = "<="
        self.shadow_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.shadow_fbo = ctx.framebuffer(depth_attachment=self.shadow_tex)

    def set_part(self, name, data):
        """Upload (or replace) a mesh part on the GPU."""
        ctx = self.ctx
        old = self.parts.pop(name, None)
        if old:
            for obj in old["_res"]:
                obj.release()
        V, I, S, sscale = data
        vbo = ctx.buffer(V.tobytes())
        ibo = ctx.buffer(I.tobytes())
        fmt = "3f 3f 3f 1f 2f 4f"
        attrs = ["in_pos", "in_nrm", "in_col", "in_ao", "in_uv", "in_seam"]
        vao = ctx.vertex_array(self.prog_mesh, [(vbo, fmt, *attrs)], ibo)
        dvao = ctx.vertex_array(self.prog_depth, [(vbo, "3f 52x", "in_pos")], ibo)
        p = {"vao": vao, "dvao": dvao, "n_studs": len(S), "scale": sscale,
             "_res": [vao, dvao, vbo, ibo]}
        if len(S):
            ib = ctx.buffer(S.tobytes())
            p["svao"] = ctx.vertex_array(self.prog_stud, [
                (self.stud_vbo, "3f 3f", "in_pos", "in_nrm"),
                (ib, "3f 3f/i", "in_ipos", "in_icol")])
            p["sdvao"] = ctx.vertex_array(self.prog_dstud, [
                (self.stud_vbo, "3f 12x", "in_pos"),
                (ib, "3f 12x/i", "in_ipos")])
            p["_res"] += [p["svao"], p["sdvao"], ib]
        self.parts[name] = p

    def set_uniforms(self, prog, vals):
        for k, v in vals.items():
            if k in prog:
                if isinstance(v, np.ndarray) and v.shape == (4, 4):
                    prog[k].write(mat_bytes(v))
                else:
                    prog[k].value = v

    def render(self, target, size, yaw, pitch_deg, zoom, focus, dist_mul, part_models,
               shadows=True):
        """part_models: {part name: extra 4x4 matrix (model space) or None = hidden}"""
        ctx = self.ctx
        mgl = self.mgl
        sc = self.scene
        c = sc["center"]
        model = np.eye(4)
        model[:3, :3] = rot_y(yaw)
        model[:3, 3] = -(model[:3, :3] @ c)          # rotate around bouquet centre
        model[1, 3] += 0.0
        # camera
        el = math.radians(CAMERA_ELEVATION_DEG + pitch_deg)
        # keep the whole bouquet in view whatever the window shape:
        # tall/narrow windows move the camera back so the width still fits
        w_, h_ = size
        aspect = w_ / max(h_, 1)
        fit = max(1.0, (sc["width"] / FILL_FRACTION_W) / aspect /
                  (sc["height"] / FILL_FRACTION))
        dist = sc["cam_dist"] * fit * dist_mul / zoom
        tgt = np.asarray(focus, np.float64)
        eye = tgt + dist * np.array([0.0, math.sin(el), math.cos(el)])
        w, h = size
        vp = perspective(CAMERA_FOV_DEG, w / h, max(1.0, dist - 120), dist + 160) @ \
            look_at(eye, tgt)
        # light (fixed in the studio, object rotates under it)
        key_dir = unit([-0.55, 0.80, 0.62])
        lr = sc["radius"] * 1.08
        light = ortho(-lr, lr, -lr, lr, 1.0, 4 * lr) @ look_at(key_dir * 2 * lr, (0, 0, 0))
        names = [n for n, m in part_models.items() if m is not None and n in self.parts]
        u = {"u_vp": vp, "u_light": light, "u_scale": 1.0}

        if shadows:
            self.shadow_fbo.use()
            self.shadow_fbo.clear(depth=1.0)
            ctx.enable(mgl.DEPTH_TEST)
            ctx.disable(mgl.CULL_FACE)
            for nme in names:
                p = self.parts[nme]
                u["u_model"] = model @ part_models[nme]
                self.set_uniforms(self.prog_depth, u)
                p["dvao"].render()
                if p["n_studs"]:
                    self.set_uniforms(self.prog_dstud, dict(u, u_scale=p["scale"]))
                    p["sdvao"].render(vertices=self.n_stud_verts, instances=p["n_studs"])

        target.use()
        ctx.viewport = (0, 0, w, h)
        target.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)
        ctx.enable(mgl.DEPTH_TEST)
        ctx.disable(mgl.CULL_FACE)
        self.shadow_tex.use(location=0)
        common = {"u_cam": tuple(eye.astype(float)), "u_key_dir": tuple(key_dir),
                  "u_fill_dir": tuple(unit([0.9, 0.25, 0.45])),
                  "u_rim_dir": tuple(unit([0.2, 0.45, -1.0])),
                  "u_shadow": 0, "u_use_shadow": int(shadows),
                  "u_shadow_texel": 1.0 / SHADOW_MAP_SIZE}
        for nme in names:
            p = self.parts[nme]
            u["u_model"] = model @ part_models[nme]
            self.set_uniforms(self.prog_mesh, dict(u, **common))
            p["vao"].render()
            if p["n_studs"]:
                self.set_uniforms(self.prog_stud, dict(u, **common, u_scale=p["scale"]))
                p["svao"].render(vertices=self.n_stud_verts, instances=p["n_studs"])


# =============================================================================
#  SCENE ASSEMBLY
# =============================================================================
def build_scene(log=print):
    t0 = time.perf_counter()
    log("building voxel bouquet ...")
    g, knot = build_bouquet()
    log("meshing ...")
    V, I, S = mesh_grid(g, seed=RANDOM_SEED)
    occ = np.array(np.nonzero(g.data)).T + g.lo
    lo, hi = occ.min(0), occ.max(0) + 1
    center = (lo + hi) / 2.0
    height = float(hi[1] - lo[1])
    radius = float(np.linalg.norm(hi - lo) / 2)
    width = float(2 * np.sqrt((occ[:, 0] + 0.5 - center[0]) ** 2 +
                              (occ[:, 2] + 0.5 - center[2]) ** 2).max())
    cam_dist = (height / FILL_FRACTION) / 2 / math.tan(math.radians(CAMERA_FOV_DEG) / 2)
    log(f"  {len(V)//4} bouquet faces, {len(S)} studs "
        f"({time.perf_counter() - t0:.1f}s)")
    return {"parts": {"bouquet": (V, I, S, 1.0)}, "knot": knot,
            "center": center, "radius": radius, "cam_dist": cam_dist,
            "height": height, "width": width}


def make_tag(scene, text):
    """Build + mesh the tag for `text`."""
    tg, tag_center, px, clean, pivot, size = build_tag(scene["knot"], text)
    TV, TI, TS = mesh_grid(tg, allow_studs=False, seed=RANDOM_SEED + 1)
    return {"data": (TV, TI, TS, px), "center": tag_center - scene["center"],
            "text": clean, "pivot": pivot, "size": size}


# =============================================================================
#  OVERLAY (2D interface drawn on top of the 3D scene)
# =============================================================================
class Overlay:
    """Draws pygame-made interface layers as textured quads with fade alpha."""

    def __init__(self, ctx):
        import moderngl
        self.mgl = moderngl
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=HUD_VS, fragment_shader=HUD_FS)
        quad = np.array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], np.float32)
        self.vao = ctx.vertex_array(self.prog, [(ctx.buffer(quad.tobytes()), "2f", "in_pos")])
        self.layers = {}

    def upload(self, key, surf, to_bytes):
        w, h = surf.get_size()
        tex = self.layers.get(key)
        if tex is None or tex.size != (w, h):
            if tex is not None:
                tex.release()
            tex = self.ctx.texture((w, h), 4)
            tex.filter = (self.mgl.LINEAR, self.mgl.LINEAR)
            self.layers[key] = tex
        tex.write(to_bytes(surf, "RGBA", True))

    def draw(self, key, pos, screen, alpha=1.0):
        tex = self.layers.get(key)
        if tex is None or alpha <= 0.003:
            return
        (x, y), (W, H), (w, h) = pos, screen, tex.size
        self.prog["u_rect"].value = (-1 + 2 * x / W, 1 - 2 * (y + h) / H,
                                     -1 + 2 * (x + w) / W, 1 - 2 * y / H)
        self.prog["u_alpha"].value = float(min(1.0, alpha))
        self.prog["u_tex"].value = 3
        tex.use(location=3)
        self.ctx.disable(self.mgl.DEPTH_TEST)
        self.ctx.enable(self.mgl.BLEND)
        self.ctx.blend_func = self.mgl.SRC_ALPHA, self.mgl.ONE_MINUS_SRC_ALPHA
        self.vao.render()
        self.ctx.disable(self.mgl.BLEND)


# =============================================================================
#  INTERFACE DESIGN (control bar, help card, message dialog, toasts)
# =============================================================================
UI_TEXT = (246, 234, 238)
UI_DIM = (176, 152, 162)
UI_ACCENT = (240, 150, 176)
UI_PANEL = (22, 14, 19, 236)
UI_BTN = (255, 255, 255, 16)
UI_BTN_HOVER = (255, 255, 255, 38)
UI_LINE = (255, 255, 255, 30)


class UI:
    def __init__(self, pygame):
        self.pg = pygame
        self._fonts = {}
        self.scale = 1.0

    def font(self, size, bold=False):
        size = max(9, int(round(size * self.scale)))
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = self.pg.font.SysFont(
                "segoeui,helveticaneue,helvetica,arial,dejavusans", size, bold=bold)
        return self._fonts[key]

    def S(self, v):
        return int(round(v * self.scale))

    # ------------------------------------------------------------- icons
    def icon(self, surf, kind, c, r, col):
        pg = self.pg
        x, y = c
        k = r
        if kind == "pause":
            w = max(2, k // 3)
            pg.draw.rect(surf, col, (x - k // 2 - 1, y - k // 2 - 1, w, k + 2), border_radius=2)
            pg.draw.rect(surf, col, (x + k // 2 - w + 1, y - k // 2 - 1, w, k + 2), border_radius=2)
        elif kind == "play":
            pg.draw.polygon(surf, col, [(x - k // 2, y - k // 2 - 1), (x - k // 2, y + k // 2 + 1),
                                        (x + k // 2 + 2, y)])
        elif kind == "minus":
            pg.draw.rect(surf, col, (x - k // 2, y - 1, k, 3), border_radius=1)
        elif kind == "plus":
            pg.draw.rect(surf, col, (x - k // 2, y - 1, k, 3), border_radius=1)
            pg.draw.rect(surf, col, (x - 1, y - k // 2, 3, k), border_radius=1)
        elif kind == "pencil":
            pg.draw.line(surf, col, (x - k // 2, y + k // 2), (x + k // 2, y - k // 2), 3)
            pg.draw.polygon(surf, col, [(x - k // 2 - 2, y + k // 2 + 2), (x - k // 2 + 3, y + k // 2),
                                        (x - k // 2, y + k // 2 - 3)])
        elif kind == "zoom":
            pg.draw.circle(surf, col, (x - 2, y - 2), k // 2, 2)
            pg.draw.line(surf, col, (x + k // 4, y + k // 4), (x + k // 2 + 2, y + k // 2 + 2), 3)
        elif kind == "full":
            a, b = k // 2 + 1, max(3, k // 3)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    cx, cy = x + sx * a, y + sy * a
                    pg.draw.line(surf, col, (cx, cy), (cx - sx * b, cy), 2)
                    pg.draw.line(surf, col, (cx, cy), (cx, cy - sy * b), 2)
        elif kind == "reverse":
            pg.draw.arc(surf, col, (x - k // 2, y - k // 2, k, k), 0.6, 5.6, 2)
            pg.draw.polygon(surf, col, [(x + k // 2 + 1, y - 4), (x + k // 2 - 4, y - 5),
                                        (x + k // 2, y + 1)])

    def pill(self, surf, rect, fill, radius=None, width=0):
        """Rounded rectangle, alpha-blended onto whatever is already drawn."""
        pg = self.pg
        r = pg.Rect(rect)
        rad = radius if radius is not None else r.h // 2
        if len(fill) == 3 or fill[3] == 255:
            pg.draw.rect(surf, fill, r, width, border_radius=rad)
            return
        tmp = pg.Surface(r.size, pg.SRCALPHA)
        pg.draw.rect(tmp, fill, (0, 0, r.w, r.h), width, border_radius=rad)
        surf.blit(tmp, r.topleft)

    def outline(self, surf, rect, col, radius, width=1):
        self.pill(surf, rect, col, radius, width)

    def toggle(self, surf, rect, on, t):
        x, y, w, h = rect
        bg = tuple(int(a + (b - a) * t) for a, b in zip((90, 80, 86), UI_ACCENT))
        self.pill(surf, rect, bg)
        knob = h - 6
        kx = x + 3 + int((w - knob - 6) * t)
        self.pg.draw.circle(surf, (255, 255, 255), (kx + knob // 2, y + h // 2), knob // 2)

    # ------------------------------------------------------------- control bar
    def build_bar(self, st, hover):
        """Returns (surface, list of (id, rect, tooltip))."""
        pg = self.pg
        S = self.S
        H = S(44)
        f = self.font(15)
        items = [
            ("pause", "play" if st["paused"] else "pause",
             "Play" if st["paused"] else "Pause", "Pause / play rotation   ·   Space"),
            ("slower", "minus", None, "Slower   ·   Left arrow"),
            ("speed", None, f"{st['speed']:.0f}°/s", None),
            ("faster", "plus", None, "Faster   ·   Right arrow"),
            ("reverse", "reverse", None, "Reverse direction   ·   R"),
            ("sep", None, None, None),
            ("tag", "toggle", "Tag", "Show / hide the tag   ·   Tab"),
            ("write", "pencil", "Write", "Write your message   ·   Enter"),
            ("closeup", "zoom", "Close-up", "Look at the tag   ·   C"),
            ("sep", None, None, None),
            ("full", "full", None, "Fullscreen   ·   F"),
            ("help", "?", None, "All controls   ·   H"),
        ]
        layout, x = [], S(8)
        for ident, ic, label, tip in items:
            if ident == "sep":
                layout.append((ident, pg.Rect(x + S(4), S(10), 1, H - S(20)), None, None, None))
                x += S(9)
                continue
            w = S(12)
            if ic == "toggle":
                w += S(34) + S(8)
            elif ic == "?":
                w += S(18)
            elif ic:
                w += S(18)
            if label:
                w += f.size(label)[0] + (S(8) if ic else 0)
            w += S(12)
            if ident in ("slower", "faster", "reverse", "full", "help"):
                w = H - S(8)
            layout.append((ident, pg.Rect(x, S(4), w, H - S(8)), ic, label, tip))
            x += w + S(4)
        width = x + S(4)
        surf = pg.Surface((width, H), pg.SRCALPHA)
        self.pill(surf, (0, 0, width, H), UI_PANEL, S(14))
        self.outline(surf, (0, 0, width, H), UI_LINE, S(14))
        hits = []
        for ident, r, ic, label, tip in layout:
            if ident == "sep":
                self.pill(surf, r, UI_LINE, 0)
                continue
            clickable = ident != "speed"
            if clickable:
                self.pill(surf, r, UI_BTN_HOVER if hover == ident else UI_BTN, S(10))
                hits.append((ident, r, tip))
            cx = r.x + S(12)
            cy = r.centery
            if ic == "toggle":
                self.toggle(surf, (cx, cy - S(10), S(34), S(20)), st["tag_on"], st["tag_t"])
                cx += S(34) + S(8)
            elif ic == "?":
                t = self.font(17, True).render("?", True, UI_TEXT)
                surf.blit(t, t.get_rect(center=r.center))
                continue
            elif ic:
                if label is None:
                    self.icon(surf, ic, r.center, S(12), UI_TEXT)
                    continue
                self.icon(surf, ic, (cx + S(7), cy), S(12), UI_TEXT)
                cx += S(18) + S(8)
            if label:
                col = UI_ACCENT if ident == "speed" else UI_TEXT
                t = f.render(label, True, col)
                if ident == "speed":
                    surf.blit(t, t.get_rect(center=r.center))
                else:
                    surf.blit(t, (cx, cy - t.get_height() // 2))
        return surf, hits

    def build_tooltip(self, text):
        pg = self.pg
        f = self.font(13)
        t = f.render(text, True, UI_TEXT)
        w, h = t.get_width() + self.S(20), t.get_height() + self.S(10)
        surf = pg.Surface((w, h), pg.SRCALPHA)
        self.pill(surf, (0, 0, w, h), (40, 26, 34, 235), self.S(8))
        surf.blit(t, (self.S(10), self.S(5)))
        return surf

    def build_toast(self, text):
        pg = self.pg
        f = self.font(17, True)
        t = f.render(text, True, UI_TEXT)
        w, h = t.get_width() + self.S(40), t.get_height() + self.S(18)
        surf = pg.Surface((w, h), pg.SRCALPHA)
        self.pill(surf, (0, 0, w, h), UI_PANEL)
        self.outline(surf, (0, 0, w, h), (240, 150, 176, 90), h // 2)
        surf.blit(t, (self.S(20), self.S(9)))
        return surf

    def keycap(self, surf, text, x, y):
        f = self.font(13, True)
        t = f.render(text, True, UI_TEXT)
        w = max(t.get_width() + self.S(14), self.S(30))
        h = self.S(24)
        self.pill(surf, (x, y, w, h), (255, 255, 255, 30), self.S(6))
        self.outline(surf, (x, y, w, h), (255, 255, 255, 50), self.S(6))
        surf.blit(t, (x + (w - t.get_width()) // 2, y + (h - t.get_height()) // 2))
        return w

    def build_help(self):
        pg = self.pg
        S = self.S
        left = [("Mouse", None), ("Drag", "Turn the bouquet"), ("Scroll", "Zoom in / out"),
                ("Double-click", "Reset the view"), ("", None), ("Tag", None),
                ("Tab", "Show / hide the tag"), ("Enter", "Write your message"),
                ("C", "Close-up of the tag")]
        right = [("Rotation", None), ("Space", "Pause / play"), ("← →", "Slower / faster"),
                 ("R", "Reverse direction"), ("", None), ("Window", None),
                 ("F", "Fullscreen"), ("M", "Maximise"), ("[  ]", "Smaller / bigger"),
                 ("S", "Shadows on / off"), ("0", "Reset view"), ("Q", "Quit")]
        W, rowh = S(720), S(32)
        rows = max(len(left), len(right))
        H = S(96) + rows * rowh + S(40)
        surf = pg.Surface((W, H), pg.SRCALPHA)
        self.pill(surf, (0, 0, W, H), UI_PANEL, S(18))
        self.outline(surf, (0, 0, W, H), UI_LINE, S(18))
        t = self.font(24, True).render("Controls", True, UI_TEXT)
        surf.blit(t, (S(32), S(26)))
        t = self.font(14).render("Press H or Esc to close", True, UI_DIM)
        surf.blit(t, (W - S(32) - t.get_width(), S(34)))
        for col, entries in enumerate((left, right)):
            x0 = S(32) + col * S(350)
            y = S(84)
            for key, desc in entries:
                if desc is None and key:
                    surf.blit(self.font(13, True).render(key.upper(), True, UI_ACCENT),
                              (x0, y + S(6)))
                elif key:
                    self.keycap(surf, key, x0, y)
                    surf.blit(self.font(15).render(desc, True, UI_TEXT), (x0 + S(118), y + S(2)))
                y += rowh
        return surf

    def build_dialog(self, buf, caret, hover):
        pg = self.pg
        S = self.S
        W, H = S(600), S(206)
        surf = pg.Surface((W, H), pg.SRCALPHA)
        self.pill(surf, (0, 0, W, H), UI_PANEL, S(18))
        self.outline(surf, (0, 0, W, H), (240, 150, 176, 110), S(18))
        surf.blit(self.font(20, True).render("Write your message", True, UI_TEXT), (S(28), S(22)))
        cnt = self.font(13).render(f"{len(buf)} / {TAG_MAX_CHARS}", True, UI_DIM)
        surf.blit(cnt, (W - S(28) - cnt.get_width(), S(28)))
        box = pg.Rect(S(28), S(62), W - S(56), S(52))
        self.pill(surf, box, (255, 255, 255, 22), S(10))
        self.outline(surf, box, (240, 150, 176, 160), S(10), 2)
        f = self.font(24, True)
        shown = buf
        while f.size(shown + "|")[0] > box.w - S(28) and shown:
            shown = shown[1:]
        t = f.render(shown, True, UI_TEXT) if shown else \
            self.font(20).render("Type here…", True, (150, 128, 138))
        surf.blit(t, (box.x + S(14), box.centery - t.get_height() // 2))
        if caret:
            cx = box.x + S(14) + (f.size(shown)[0] if shown else 0) + S(2)
            pg.draw.rect(surf, UI_ACCENT, (cx, box.centery - S(13), S(2), S(26)))
        hint = self.font(13).render("Letters, numbers, spaces and  - . , ! ? ' & +      * makes a heart",
                                    True, UI_DIM)
        surf.blit(hint, (S(30), S(124)))
        hits = []
        bx = W - S(28)
        for ident, label, primary in (("apply", "Apply  (Enter)", True), ("cancel", "Cancel  (Esc)", False)):
            tw = self.font(15, True).size(label)[0]
            r = pg.Rect(bx - tw - S(36), H - S(54), tw + S(36), S(36))
            fill = (UI_ACCENT + (255,)) if primary else (UI_BTN_HOVER if hover == ident else UI_BTN)
            if primary and hover == ident:
                fill = (250, 172, 194, 255)
            self.pill(surf, r, fill, S(10))
            t = self.font(15, True).render(label, True, (40, 16, 26) if primary else UI_TEXT)
            surf.blit(t, t.get_rect(center=r.center))
            hits.append((ident, r))
            bx = r.x - S(10)
        return surf, hits

    def build_loading(self, msg, frac):
        pg = self.pg
        S = self.S
        W, H = S(420), S(120)
        surf = pg.Surface((W, H), pg.SRCALPHA)
        t = self.font(22, True).render("Voxel Bouquet", True, UI_TEXT)
        surf.blit(t, t.get_rect(center=(W // 2, S(26))))
        t = self.font(14).render(msg, True, UI_DIM)
        surf.blit(t, t.get_rect(center=(W // 2, S(62))))
        self.pill(surf, (S(60), S(88), W - S(120), S(6)), (255, 255, 255, 30))
        self.pill(surf, (S(60), S(88), max(S(6), int((W - S(120)) * frac)), S(6)), UI_ACCENT)
        return surf


def window_icon(pygame):
    """A tiny pixel rose for the title bar."""
    art = ["....GG....", "..PPPPPP..", ".PPRRRRPP.", ".PRRPPRRP.", ".PRPRRPRP.",
           ".PRRPPRRP.", "..PRRRRP..", "...PPPP...", "..L.GG.L..", "...LGGL...",
           "....GG....", "....GG...."]
    cols = {"P": (240, 150, 170), "R": (190, 50, 85), "G": (80, 140, 80), "L": (120, 170, 100)}
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch in cols:
                s.set_at((x, y), cols[ch] + (255,))
    return pygame.transform.scale(s, (40, 48))


# =============================================================================
#  APPLICATION
# =============================================================================
def parse_args():
    ap = argparse.ArgumentParser(description="Voxel Bouquet - a 3D brick-built flower bouquet")
    ap.add_argument("--text", default=TAG_DEFAULT_TEXT, help="message on the tag")
    ap.add_argument("--no-tag", action="store_true", help="start without the tag")
    ap.add_argument("--speed", type=float, default=ROTATION_SPEED_DEG,
                    help="rotation speed in degrees per second")
    ap.add_argument("--size", default=f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
    ap.add_argument("--fullscreen", action="store_true", help="start in fullscreen")
    ap.add_argument("--maximized", action="store_true", help="start maximised")
    return ap.parse_args()


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def translate(p):
    m = np.eye(4)
    m[:3, 3] = p
    return m


def rot4(axis, a):
    c, s_ = math.cos(a), math.sin(a)
    m = np.eye(4)
    if axis == "z":
        m[:2, :2] = [[c, -s_], [s_, c]]
    else:
        m[1:3, 1:3] = [[c, -s_], [s_, c]]
    return m


def main():
    import warnings
    import pygame
    import moderngl

    args = parse_args()
    W, H = (int(v) for v in args.size.lower().split("x"))
    pygame.init()
    pygame.display.set_caption("Voxel Bouquet")
    try:
        pygame.display.set_icon(window_icon(pygame))
    except Exception:
        pass
    gl = pygame.display.gl_set_attribute
    gl(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    gl(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    gl(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    if sys.platform == "darwin":
        gl(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
    gl(pygame.GL_DEPTH_SIZE, 24)
    flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
    try:
        gl(pygame.GL_MULTISAMPLEBUFFERS, 1)
        gl(pygame.GL_MULTISAMPLESAMPLES, MSAA_SAMPLES)
        pygame.display.set_mode((W, H), flags, vsync=1)
    except Exception:
        gl(pygame.GL_MULTISAMPLEBUFFERS, 0)
        gl(pygame.GL_MULTISAMPLESAMPLES, 0)
        pygame.display.set_mode((W, H), flags)
    ctx = moderngl.create_context()
    to_bytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring

    # ---------------------------------------------------------- window helpers
    win = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            win = pygame.Window.from_display_module()
            win.resizable = True
            win.minimum_size = MIN_WINDOW
    except Exception:
        win = None
    try:
        desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
    except Exception:
        desk_w, desk_h = 1920, 1080
    full = {"on": False}

    def resize_window(factor):
        if win is None or full["on"]:
            return
        cw, ch = pygame.display.get_window_size()
        try:
            win.size = (int(min(max(cw * factor, MIN_WINDOW[0]), desk_w * 0.98)),
                        int(min(max(ch * factor, MIN_WINDOW[1]), desk_h * 0.92)))
            win.position = pygame.WINDOWPOS_CENTERED
        except Exception:
            pass

    def toggle_fullscreen():
        try:
            if win is not None:
                win.set_windowed() if full["on"] else win.set_fullscreen(desktop=True)
            else:
                pygame.display.toggle_fullscreen()
            full["on"] = not full["on"]
        except Exception:
            pass

    def toggle_maximize():
        if win is None or full["on"]:
            return
        try:
            cw, ch = pygame.display.get_window_size()
            win.restore() if (cw >= desk_w * 0.9 and ch >= desk_h * 0.8) else win.maximize()
        except Exception:
            pass

    # ---------------------------------------------------------- loading screen
    ui = UI(pygame)
    ov = Overlay(ctx)

    def loading(msg, frac):
        ui.scale = max(0.8, min(1.5, min(W / 1280, H / 820)))
        surf = ui.build_loading(msg, frac)
        ov.upload("loading", surf, to_bytes)
        ctx.screen.use()
        ctx.viewport = (0, 0, W, H)
        ctx.clear(0, 0, 0, 1)
        ov.draw("loading", ((W - surf.get_width()) // 2, (H - surf.get_height()) // 2), (W, H))
        pygame.display.flip()
        pygame.event.pump()

    steps = iter([("Arranging the flowers…", 0.15), ("Assembling the bricks…", 0.6)])

    def log(m):
        try:
            msg, fr = next(steps)
            loading(msg, fr)
        except StopIteration:
            pass
    loading("Opening the box…", 0.05)
    scene = build_scene(log=log)
    loading("Wrapping it up…", 0.9)
    rend = Renderer(ctx, scene)

    # ---------------------------------------------------------- tag state
    tag = {}

    def set_text(text):
        info = make_tag(scene, text)
        rend.set_part("tag", info["data"])
        tag.update(info)
    set_text(args.text)
    committed_text = tag["text"]

    # ---------------------------------------------------------- app state
    st = {"paused": False, "speed": args.speed, "tag_on": not args.no_tag,
          "tag_t": 0.0 if args.no_tag else 1.0}
    direction = 1.0
    shadows = True
    yaw = math.radians(START_YAW_DEG)
    pitch = 0.0
    zoom = 1.0
    dragging = False
    drag_moved = False
    last = (0, 0)
    last_click = 0.0
    closeup = False
    focus = np.zeros(3)
    dist_mul = 1.0
    now0 = time.perf_counter()
    tag_anim = {"mode": "idle" if not args.no_tag else "hidden", "t0": now0}
    swing = {"t0": now0, "amp": 0.0}
    help_open = False
    editing = False
    edit_buf = ""
    edit_dirty_t = None
    restore_closeup = False
    swallow = ""
    last_input = now0
    bar_alpha = 1.0
    toast = {"text": "Press Enter to write your own message", "t0": now0, "dur": 5.0}
    toast_built = None
    bar_key = None
    bar_hits, bar_pos = [], (0, 0)
    dlg_hits, dlg_pos = [], (0, 0)
    tip_key = None
    help_key = None
    hover = None
    cursor_visible = True

    if args.fullscreen:
        toggle_fullscreen()
    elif args.maximized:
        toggle_maximize()

    def show_toast(text, dur=1.6):
        toast.update(text=text, t0=time.perf_counter(), dur=dur)

    def set_tag(on):
        nonlocal closeup
        if on == st["tag_on"]:
            return
        st["tag_on"] = on
        tag_anim.update(mode="in" if on else "out", t0=time.perf_counter())
        if on:
            swing.update(t0=time.perf_counter(), amp=math.radians(16))
        else:
            closeup = False
        show_toast("Tag added" if on else "Tag removed")

    def open_editor():
        nonlocal editing, edit_buf, restore_closeup, closeup
        editing = True
        edit_buf = "" if tag["text"] == clean_name(TAG_DEFAULT_TEXT) else tag["text"]
        restore_closeup = closeup
        closeup = True
        set_tag(True)
        pygame.key.start_text_input()

    def close_editor(apply):
        nonlocal editing, committed_text, closeup, edit_dirty_t
        editing = False
        edit_dirty_t = None
        pygame.key.stop_text_input()
        closeup = restore_closeup
        if apply and clean_name(edit_buf):
            set_text(edit_buf)
            committed_text = tag["text"]
            swing.update(t0=time.perf_counter(), amp=math.radians(9))
            show_toast("Message updated")
        elif tag["text"] != committed_text:
            set_text(committed_text)

    def action(ident):
        nonlocal direction, closeup, help_open, zoom, pitch, yaw
        if ident == "pause":
            st["paused"] = not st["paused"]
            show_toast("Paused" if st["paused"] else "Playing")
        elif ident == "slower":
            st["speed"] = max(0.0, st["speed"] - 4.0)
        elif ident == "faster":
            st["speed"] = min(180.0, st["speed"] + 4.0)
        elif ident == "reverse":
            direction = -direction
            show_toast("Direction reversed")
        elif ident == "tag":
            set_tag(not st["tag_on"])
        elif ident == "write":
            open_editor()
        elif ident == "closeup":
            if not st["tag_on"]:
                set_tag(True)
            closeup = not closeup
        elif ident == "full":
            toggle_fullscreen()
        elif ident == "help":
            help_open = not help_open

    clock = pygame.time.Clock()
    t_prev = time.perf_counter()
    running = True
    while running:
        now = time.perf_counter()
        dt = min(now - t_prev, 0.1)
        t_prev = now
        ui.scale = max(0.8, min(1.5, min(W / 1280, H / 820)))

        for e in pygame.event.get():
            if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN,
                          pygame.MOUSEWHEEL):
                last_input = now
            if e.type == pygame.QUIT:
                running = False

            # ---------------- message dialog
            elif editing and e.type == pygame.TEXTINPUT:
                txt = e.text
                if swallow and txt.lower() == swallow:
                    txt = ""
                swallow = ""
                for ch in txt.upper():
                    if len(edit_buf) >= TAG_MAX_CHARS:
                        break
                    if ch == " ":
                        if edit_buf and not edit_buf.endswith(" "):
                            edit_buf += " "
                    elif ch in PIXEL_FONT:
                        edit_buf += ch
                edit_dirty_t = now
            elif editing and e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    close_editor(True)
                elif e.key == pygame.K_ESCAPE:
                    close_editor(False)
                elif e.key == pygame.K_BACKSPACE:
                    edit_buf = edit_buf[:-1]
                    edit_dirty_t = now
            elif editing and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos[0] - dlg_pos[0], e.pos[1] - dlg_pos[1]
                for ident, r in dlg_hits:
                    if r.collidepoint(mx, my):
                        close_editor(ident == "apply")

            # ---------------- keys
            elif e.type == pygame.KEYDOWN:
                k = e.key
                if help_open and k in (pygame.K_ESCAPE, pygame.K_h, pygame.K_SLASH):
                    help_open = False
                elif k == pygame.K_ESCAPE:
                    if full["on"]:
                        toggle_fullscreen()
                    elif closeup:
                        closeup = False
                elif k == pygame.K_q:
                    running = False
                elif k == pygame.K_TAB:
                    action("tag")
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
                    swallow = (e.unicode or "").lower() if k == pygame.K_e else ""
                    action("write")
                elif k == pygame.K_SPACE:
                    action("pause")
                elif k in (pygame.K_RIGHT, pygame.K_UP, pygame.K_PLUS, pygame.K_EQUALS,
                           pygame.K_KP_PLUS):
                    action("faster")
                elif k in (pygame.K_LEFT, pygame.K_DOWN, pygame.K_MINUS, pygame.K_KP_MINUS):
                    action("slower")
                elif k == pygame.K_r:
                    action("reverse")
                elif k in (pygame.K_c, pygame.K_t):
                    action("closeup")
                elif k in (pygame.K_f, pygame.K_F11):
                    toggle_fullscreen()
                elif k in (pygame.K_m, pygame.K_F10):
                    toggle_maximize()
                elif k == pygame.K_RIGHTBRACKET:
                    resize_window(1.15)
                elif k == pygame.K_LEFTBRACKET:
                    resize_window(1 / 1.15)
                elif k == pygame.K_s:
                    shadows = not shadows
                    show_toast("Shadows on" if shadows else "Shadows off")
                elif k in (pygame.K_h, pygame.K_SLASH):
                    help_open = not help_open
                elif k in (pygame.K_0, pygame.K_HOME):
                    zoom, pitch, closeup = 1.0, 0.0, False
                    yaw = math.radians(START_YAW_DEG)

            # ---------------- mouse
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                hit = None
                if bar_alpha > 0.3 and not help_open:
                    mx, my = e.pos[0] - bar_pos[0], e.pos[1] - bar_pos[1]
                    for ident, r, _ in bar_hits:
                        if r.collidepoint(mx, my):
                            hit = ident
                if hit:
                    action(hit)
                elif help_open:
                    help_open = False
                else:
                    if now - last_click < 0.35:
                        zoom, pitch, closeup = 1.0, 0.0, False
                    last_click = now
                    dragging, drag_moved, last = True, False, e.pos
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging = False
            elif e.type == pygame.MOUSEMOTION:
                if dragging:
                    dx, dy = e.pos[0] - last[0], e.pos[1] - last[1]
                    last = e.pos
                    yaw += dx * 0.008
                    pitch = float(np.clip(pitch + dy * 0.25, -30, 60))
                    drag_moved = True
            elif e.type == pygame.MOUSEWHEEL and not editing:
                zoom = float(np.clip(zoom * (1.1 ** e.y), 0.5, 6.0))

        # ---------------- window size (any resize method)
        nw, nh = pygame.display.get_window_size()
        if (nw, nh) != (W, H):
            W, H = nw, nh
            bar_key = None
            help_key = None
        if W < 2 or H < 2:
            clock.tick(15)
            continue

        # ---------------- live tag preview while typing
        if editing and edit_dirty_t is not None and now - edit_dirty_t > 0.08:
            edit_dirty_t = None
            set_text(edit_buf if clean_name(edit_buf) else committed_text)

        # ---------------- tag animation (unfurl / shrink + pendulum swing)
        ta = now - tag_anim["t0"]
        if tag_anim["mode"] == "in":
            u = min(1.0, ta / 0.75)
            tag_scale = max(0.0, ease_out_back(u))
            st["tag_t"] = u
            if u >= 1.0:
                tag_anim["mode"] = "idle"
        elif tag_anim["mode"] == "out":
            u = min(1.0, ta / 0.38)
            tag_scale = (1.0 - u) ** 2
            st["tag_t"] = 1.0 - u
            if u >= 1.0:
                tag_anim["mode"] = "hidden"
        elif tag_anim["mode"] == "hidden":
            tag_scale, st["tag_t"] = 0.0, 0.0
        else:
            tag_scale, st["tag_t"] = 1.0, 1.0
        sw_t = now - swing["t0"]
        ang = swing["amp"] * math.exp(-2.2 * sw_t) * math.sin(7.0 * sw_t)
        ang2 = swing["amp"] * 0.45 * math.exp(-2.0 * sw_t) * math.sin(5.3 * sw_t + 0.8)
        part_models = {"bouquet": np.eye(4), "tag": None}
        if tag_scale > 0.002:
            pv = tag["pivot"]
            sm = np.eye(4)
            sm[:3, :3] *= tag_scale
            part_models["tag"] = translate(pv) @ rot4("z", ang) @ rot4("x", ang2) @ sm @ \
                translate(-pv)

        # ---------------- camera
        if closeup and st["tag_on"]:
            goal_yaw = math.radians(-12.0)
            d = math.atan2(math.sin(goal_yaw - yaw), math.cos(goal_yaw - yaw))
            yaw += d * min(1.0, dt * 3.0)
            tw, th = tag["size"]
            goal_focus = rot_y(yaw) @ tag["center"]
            goal_dist = float(np.clip(0.13 * max(tw / 12.0, th / 4.0), 0.12, 0.42))
            if editing:                       # leave room for the dialog above
                goal_focus = goal_focus + np.array([0, th * 0.9 + 2.2, 0]) * 0.55
        else:
            if not st["paused"] and not dragging:
                yaw += math.radians(st["speed"]) * direction * dt
            goal_focus = np.zeros(3)
            goal_dist = 1.0
        a = min(1.0, dt * 3.5)
        focus = focus + (goal_focus - focus) * a
        dist_mul = dist_mul + (goal_dist - dist_mul) * a

        rend.render(ctx.screen, (W, H), yaw, pitch, zoom, focus, dist_mul, part_models,
                    shadows=shadows)

        # ---------------- interface
        idle = now - last_input
        want_bar = 1.0 if (idle < UI_HIDE_AFTER or help_open or editing) else 0.0
        bar_alpha += (want_bar - bar_alpha) * min(1.0, dt * (6.0 if want_bar else 2.5))
        if editing:
            bar_alpha = min(bar_alpha, 0.0)
        mx, my = pygame.mouse.get_pos()
        hover = None
        if bar_alpha > 0.3 and not help_open and not editing:
            for ident, r, tip in bar_hits:
                if r.collidepoint(mx - bar_pos[0], my - bar_pos[1]):
                    hover = ident
        key = (round(st["speed"]), st["paused"], st["tag_on"], round(st["tag_t"], 2), hover,
               ui.scale)
        if key != bar_key:
            bar_key = key
            surf, bar_hits = ui.build_bar(st, hover)
            ov.upload("bar", surf, to_bytes)
            bar_pos = ((W - surf.get_width()) // 2, H - surf.get_height() - ui.S(20))
        ov.draw("bar", bar_pos, (W, H), bar_alpha)
        # tooltip
        tip = next((t for i, r, t in bar_hits if i == hover and t), None)
        if tip:
            if tip != tip_key:
                tip_key = tip
                ov.upload("tip", ui.build_tooltip(tip), to_bytes)
            tw = ov.layers["tip"].size[0]
            ov.draw("tip", (int(np.clip(mx - tw // 2, 8, W - tw - 8)),
                            bar_pos[1] - ui.S(40)), (W, H), bar_alpha)
        # toast
        tt = now - toast["t0"]
        if toast["text"] and tt < toast["dur"] + 0.45:
            if toast_built != (toast["text"], ui.scale):
                toast_built = (toast["text"], ui.scale)
                ov.upload("toast", ui.build_toast(toast["text"]), to_bytes)
            al = min(1.0, tt / 0.2) * (1.0 - max(0.0, tt - toast["dur"]) / 0.45)
            tw = ov.layers["toast"].size[0]
            ov.draw("toast", ((W - tw) // 2, ui.S(26) + int((1 - min(1, tt / 0.2)) * -12)),
                    (W, H), al)
        # help
        if help_open:
            if help_key != ui.scale:
                help_key = ui.scale
                ov.upload("help", ui.build_help(), to_bytes)
            hw, hh = ov.layers["help"].size
            ov.draw("help", ((W - hw) // 2, max(10, (H - hh) // 2 - ui.S(30))), (W, H))
        # dialog
        if editing:
            caret = int(now * 2) % 2 == 0
            dh = None
            for ident, r in dlg_hits:
                if r.collidepoint(mx - dlg_pos[0], my - dlg_pos[1]):
                    dh = ident
            surf, dlg_hits = ui.build_dialog(edit_buf, caret, dh)
            ov.upload("dialog", surf, to_bytes)
            dlg_pos = ((W - surf.get_width()) // 2, ui.S(30))
            ov.draw("dialog", dlg_pos, (W, H))

        # hide the mouse pointer when the interface has faded (nice for recording)
        want_cursor = bar_alpha > 0.05 or dragging or help_open or editing
        if want_cursor != cursor_visible:
            cursor_visible = want_cursor
            pygame.mouse.set_visible(want_cursor)

        pygame.display.flip()
        clock.tick(TARGET_FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
