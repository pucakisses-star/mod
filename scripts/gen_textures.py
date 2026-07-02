#!/usr/bin/env python3
"""Deterministically generates every PNG asset for the Underground Villages mod.

Derives entity/armor textures from vanilla 1.21.1 reference textures and
paints block/item/icon textures procedurally with fixed RNG seeds.

Usage:
    python3 scripts/gen_textures.py [--vanilla <path-to-vanilla-textures-root>]

The vanilla root must point at .../assets/minecraft/textures (containing
villager/, zombie_villager/, illager/, models/armor/, block/ ...).
"""

import argparse
import os
import random
import sys

from PIL import Image

DEFAULT_VANILLA = (
    "/tmp/claude-0/-home-user-mod/84c799a8-4b72-5c74-a265-190e1f940a93/"
    "scratchpad/vanilla/assets/minecraft/textures"
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO_ROOT, "src/main/resources/assets/undergroundvillages")

TRANSPARENT = (0, 0, 0, 0)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def out_path(rel):
    p = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save(im, rel):
    im.save(out_path(rel), optimize=True)
    print("wrote", os.path.join("assets/undergroundvillages", rel))


def lum(px):
    return 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]


def clamp(v):
    return max(0, min(255, int(round(v))))


def rect(im, x0, y0, x1, y1, color):
    """Fill [x0,x1) x [y0,y1) with color."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            im.putpixel((x, y), color)


def noise_rect(im, x0, y0, x1, y1, base, rng, jitter=8):
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-jitter, jitter)
            im.putpixel((x, y), (clamp(base[0] + d), clamp(base[1] + d),
                                 clamp(base[2] + d), 255))


def remap(im, box, tone, pivot, pred=None):
    """Luminance-remap opaque pixels of box to shades of tone."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px = im.getpixel((x, y))
            if px[3] == 0:
                continue
            if pred is not None and not pred(px):
                continue
            g = lum(px) / pivot
            im.putpixel((x, y), (clamp(tone[0] * g), clamp(tone[1] * g),
                                 clamp(tone[2] * g), px[3]))


def is_skin(px):
    r, g, b = px[0], px[1], px[2]
    return px[3] > 0 and r > 100 and r > g > b and (r - b) > 25


# --------------------------------------------------------------------------
# villager 64x64 UV regions (Mojang VillagerModel / ZombieVillagerModel)
# --------------------------------------------------------------------------
HEAD_ALL = (0, 0, 32, 18)          # top/bottom row + 4 side faces
HEAD_SIDES = (0, 8, 32, 18)        # right, front, left, back
NOSE = (24, 0, 32, 6)
HAT_TOP = (40, 0, 48, 8)
HAT_SIDES = (32, 8, 64, 18)
HAT_FRONT = (40, 8, 48, 18)
BODY_TOP = (22, 20, 30, 26)
BODY_FRONT = (22, 26, 30, 38)
BODY_RIGHT = (16, 26, 22, 38)
BODY_LEFT = (30, 26, 36, 38)
BODY_BACK = (36, 26, 44, 38)
BODY_ALL = (16, 20, 44, 38)
JACKET_TOP = (6, 38, 14, 44)
JACKET_FRONT = (6, 44, 14, 56)
JACKET_RIGHT = (0, 44, 6, 56)
JACKET_LEFT = (14, 44, 20, 56)
JACKET_BACK = (20, 44, 28, 56)
ARM = (44, 22, 60, 34)             # hanging arm segment (mirrored for both)
ARM_TOP = (48, 22, 52, 26)         # shoulder, seen from above
ARMS_CROSS = (40, 38, 64, 46)      # crossed-arms piece
ARMS_CROSS_FRONT = (44, 42, 52, 46)   # hands
ARMS_CROSS_BOTTOM = (52, 38, 60, 42)  # underside of hands
LEGS = (0, 22, 16, 38)


# ==========================================================================
# BLOCK TEXTURES
# ==========================================================================

def gen_prospecting_table_top(van):
    rng = random.Random(101)
    im = Image.open(os.path.join(van, "block/stone.png")).convert("RGBA").copy()
    # ore flecks: coal, iron, copper, gold clusters
    flecks = [
        ((45, 45, 45), [(2, 2), (3, 2), (2, 3)]),          # coal
        ((216, 175, 147), [(12, 3), (13, 3), (13, 4)]),    # iron
        ((224, 128, 78), [(3, 12), (4, 12), (4, 13)]),     # copper
        ((250, 238, 77), [(13, 12), (12, 13)]),            # gold
        ((45, 45, 45), [(8, 14), (9, 14)]),                # coal
        ((216, 175, 147), [(1, 8)]),                        # iron
    ]
    for color, cells in flecks:
        for (x, y) in cells:
            d = rng.randint(-10, 10)
            im.putpixel((x, y), (clamp(color[0] + d), clamp(color[1] + d),
                                 clamp(color[2] + d), 255))
    # pickaxe motif in the center: diagonal handle + grey head arc
    handle = (109, 74, 39)
    handle_d = (84, 55, 28)
    head = (86, 86, 92)
    head_l = (128, 128, 136)
    for i in range(6):  # handle from lower-left to upper-right
        im.putpixel((5 + i, 11 - i), handle if i % 2 == 0 else handle_d)
    # pick head arc perpendicular to the handle tip
    for (x, y), c in [((8, 4), head), ((9, 4), head_l), ((10, 4), head),
                      ((11, 5), head), ((12, 6), head), ((12, 7), head),
                      ((7, 4), head), ((6, 5), head), ((5, 6), head_l),
                      ((5, 7), head)]:
        im.putpixel((x, y), c)
    # subtle worn border
    for x in range(16):
        for y in (0, 15):
            px = im.getpixel((x, y))
            im.putpixel((x, y), (clamp(px[0] - 14), clamp(px[1] - 14),
                                 clamp(px[2] - 14), 255))
    save(im, "textures/block/prospecting_table_top.png")


def _planks(rng, base):
    im = Image.new("RGBA", (16, 16))
    seam = (clamp(base[0] * 0.55), clamp(base[1] * 0.55), clamp(base[2] * 0.55), 255)
    for y in range(16):
        for x in range(16):
            d = rng.randint(-9, 9)
            g = -6 if (x * 7 + y * 3) % 11 == 0 else 0  # sparse grain
            im.putpixel((x, y), (clamp(base[0] + d + g), clamp(base[1] + d + g),
                                 clamp(base[2] + d + g), 255))
    for y in (3, 7, 11, 15):  # plank seams
        for x in range(16):
            im.putpixel((x, y), seam)
    # staggered plank ends
    for (x, y0) in [(4, 0), (11, 4), (6, 8), (13, 12)]:
        for y in range(y0, y0 + 3):
            im.putpixel((x, y), seam)
    return im


def gen_prospecting_table_side(van):
    rng = random.Random(102)
    im = _planks(rng, (146, 116, 71))
    # stone counter-top band (matches the stone top face)
    stone = Image.open(os.path.join(van, "block/stone.png")).convert("RGBA")
    for y in range(0, 3):
        for x in range(16):
            px = stone.getpixel((x, y + 4))
            im.putpixel((x, y), (clamp(px[0] - 8), clamp(px[1] - 8),
                                 clamp(px[2] - 8), 255))
    sil = (52, 40, 26, 255)  # dark tool silhouettes hanging on the planks
    # pickaxe silhouette (left)
    for i in range(5):
        im.putpixel((3, 5 + i), sil)                 # vertical handle
    for (x, y) in [(1, 5), (2, 4), (3, 4), (4, 4), (5, 5)]:  # head
        im.putpixel((x, y), sil)
    # shovel silhouette (right)
    for i in range(4):
        im.putpixel((11, 4 + i), sil)                # handle
    for (x, y) in [(10, 8), (11, 8), (12, 8), (10, 9), (11, 9), (12, 9), (11, 10)]:
        im.putpixel((x, y), sil)                     # blade
    save(im, "textures/block/prospecting_table_side.png")


def gen_prospecting_table_bottom(van):
    rng = random.Random(103)
    im = _planks(rng, (117, 92, 55))
    save(im, "textures/block/prospecting_table_bottom.png")


def gen_tavern_hearth_side(van):
    rng = random.Random(104)
    im = Image.new("RGBA", (16, 16))
    mortar = (46, 38, 34, 255)
    brick_base = (104, 62, 47)
    # dark warm bricks, 8x4 pattern with offset rows
    for y in range(16):
        for x in range(16):
            d = rng.randint(-10, 10)
            im.putpixel((x, y), (clamp(brick_base[0] + d),
                                 clamp(brick_base[1] + d),
                                 clamp(brick_base[2] + d), 255))
    for row in range(4):
        y = row * 4 + 3
        for x in range(16):
            im.putpixel((x, y), mortar)
        off = 0 if row % 2 == 0 else 4
        for x in (off, off + 8):
            for yy in range(row * 4, row * 4 + 3):
                im.putpixel((x % 16, yy), mortar)
    # warm glow leaking through cracks in the lower mortar joints
    glow_hot = (255, 196, 92, 255)
    glow = (232, 128, 40, 255)
    glow_dim = (166, 76, 26, 255)
    for (x, y), c in [((2, 11), glow), ((3, 11), glow_hot), ((4, 11), glow),
                      ((10, 11), glow), ((11, 11), glow_dim),
                      ((6, 15), glow), ((7, 15), glow_hot), ((8, 15), glow),
                      ((13, 15), glow_dim), ((14, 15), glow),
                      ((4, 12), glow_dim), ((8, 7), glow_dim), ((9, 7), glow),
                      ((12, 12), glow_dim)]:
        im.putpixel((x, y), c)
    save(im, "textures/block/tavern_hearth_side.png")


def gen_tavern_hearth_top(van):
    rng = random.Random(105)
    im = Image.new("RGBA", (16, 16))
    # charcoal bed
    for y in range(16):
        for x in range(16):
            d = rng.randint(-8, 8)
            im.putpixel((x, y), (clamp(38 + d), clamp(28 + d), clamp(25 + d), 255))
    # glowing ember cells: bright core, warm halo
    cores = [(3, 3), (9, 2), (13, 5), (5, 8), (11, 9), (2, 12), (8, 13), (14, 12)]
    for (cx, cy) in cores:
        hot = rng.random() < 0.6
        core = (255, 230, 120, 255) if hot else (255, 176, 64, 255)
        halo = (226, 112, 32, 255)
        edge = (140, 58, 22, 255)
        im.putpixel((cx, cy), core)
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = cx + dx, cy + dy
            if 0 <= x < 16 and 0 <= y < 16 and rng.random() < 0.85:
                im.putpixel((x, y), halo)
        for (dx, dy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x, y = cx + dx, cy + dy
            if 0 <= x < 16 and 0 <= y < 16 and rng.random() < 0.5:
                im.putpixel((x, y), edge)
    save(im, "textures/block/tavern_hearth_top.png")


# ==========================================================================
# ITEM TEXTURES
# ==========================================================================

def gen_mining_hat_item(van):
    im = Image.new("RGBA", (16, 16), TRANSPARENT)
    yel = (247, 198, 35, 255)
    yel_l = (255, 226, 96, 255)
    yel_d = (196, 148, 20, 255)
    outline = (92, 66, 12, 255)
    brim = (208, 208, 214, 255)
    brim_d = (150, 150, 158, 255)
    # dome
    rect(im, 5, 3, 11, 4, yel)
    rect(im, 4, 4, 12, 6, yel)
    rect(im, 3, 6, 13, 10, yel)
    # shading / highlight
    rect(im, 4, 4, 6, 8, yel_l)
    rect(im, 11, 5, 13, 10, yel_d)
    rect(im, 9, 8, 13, 10, yel_d)
    # ridge on top
    rect(im, 7, 2, 9, 3, yel_d)
    rect(im, 7, 3, 9, 9, yel_l)
    # brim
    rect(im, 2, 10, 14, 11, brim)
    rect(im, 2, 11, 14, 12, brim_d)
    # lamp: grey casing + white lens
    rect(im, 6, 5, 10, 9, brim_d)
    rect(im, 7, 6, 9, 8, (255, 255, 255, 255))
    im.putpixel((7, 6), (255, 255, 210, 255))
    # outline pass
    for y in range(16):
        for x in range(16):
            if im.getpixel((x, y))[3] == 0:
                continue
            edge = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 16 and 0 <= ny < 16) or im.getpixel((nx, ny))[3] == 0:
                    edge = True
            if edge and im.getpixel((x, y)) not in ((255, 255, 255, 255),):
                px = im.getpixel((x, y))
                im.putpixel((x, y), (clamp(px[0] * 0.55), clamp(px[1] * 0.55),
                                     clamp(px[2] * 0.55), 255))
    im.putpixel((2, 11), outline)
    im.putpixel((13, 11), outline)
    save(im, "textures/item/mining_hat.png")


def gen_wolf_whistle_item(van):
    im = Image.new("RGBA", (16, 16), TRANSPARENT)
    bone = (238, 233, 218, 255)
    bone_d = (196, 188, 168, 255)
    bone_dd = (140, 132, 112, 255)
    cord = (110, 78, 46, 255)
    # lanyard loop (top-left)
    for (x, y) in [(3, 2), (2, 3), (2, 4), (3, 5), (4, 4), (4, 3)]:
        im.putpixel((x, y), cord)
    im.putpixel((4, 5), cord)
    im.putpixel((5, 6), cord)
    # whistle barrel: diagonal from upper-left to lower-right
    body = [(5, 7), (6, 7), (7, 7),
            (5, 8), (6, 8), (7, 8), (8, 8), (9, 8),
            (6, 9), (7, 9), (8, 9), (9, 9), (10, 9), (11, 9),
            (7, 10), (8, 10), (9, 10), (10, 10), (11, 10), (12, 10),
            (8, 11), (9, 11), (10, 11), (11, 11), (12, 11),
            (9, 12), (10, 12), (11, 12)]
    for (x, y) in body:
        im.putpixel((x, y), bone)
    # mouthpiece tip
    rect(im, 12, 8, 14, 10, bone)
    im.putpixel((13, 8), bone_d)
    # round chamber shading
    for (x, y) in [(6, 9), (7, 10), (8, 11), (9, 12), (10, 12), (11, 12),
                   (12, 11), (5, 8)]:
        im.putpixel((x, y), bone_d)
    # sound hole
    im.putpixel((8, 9), bone_dd)
    im.putpixel((9, 9), (60, 54, 44, 255))
    im.putpixel((9, 10), bone_dd)
    # outline
    for y in range(16):
        for x in range(16):
            px = im.getpixel((x, y))
            if px[3] == 0 or px == cord:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 16 and 0 <= ny < 16) or im.getpixel((nx, ny))[3] == 0:
                    im.putpixel((x, y), (clamp(px[0] * 0.72), clamp(px[1] * 0.72),
                                         clamp(px[2] * 0.72), 255))
                    break
    save(im, "textures/item/wolf_whistle.png")


def gen_cat_bell_item(van):
    im = Image.new("RGBA", (16, 16), TRANSPARENT)
    gold = (244, 196, 48, 255)
    gold_l = (255, 232, 120, 255)
    gold_d = (178, 132, 20, 255)
    gold_dd = (120, 86, 12, 255)
    red = (176, 42, 42, 255)
    red_d = (120, 26, 26, 255)
    # red strap ribbon
    rect(im, 5, 2, 11, 4, red)
    rect(im, 5, 3, 11, 4, red_d)
    rect(im, 7, 1, 9, 2, red)
    # bell body (sphere bell)
    rect(im, 6, 4, 10, 5, gold)
    rect(im, 5, 5, 11, 6, gold)
    rect(im, 4, 6, 12, 10, gold)
    rect(im, 5, 10, 11, 11, gold)
    rect(im, 6, 11, 10, 12, gold_d)
    # highlight / shading
    rect(im, 5, 6, 7, 8, gold_l)
    im.putpixel((6, 5), gold_l)
    rect(im, 10, 6, 12, 10, gold_d)
    rect(im, 8, 9, 10, 10, gold_d)
    # slit + hole
    for x in range(5, 11):
        im.putpixel((x, 9), gold_dd)
    rect(im, 7, 10, 9, 11, gold_dd)
    im.putpixel((7, 10), (40, 28, 6, 255))
    im.putpixel((8, 10), (40, 28, 6, 255))
    # outline
    for y in range(16):
        for x in range(16):
            px = im.getpixel((x, y))
            if px[3] == 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 16 and 0 <= ny < 16) or im.getpixel((nx, ny))[3] == 0:
                    im.putpixel((x, y), (clamp(px[0] * 0.6), clamp(px[1] * 0.6),
                                         clamp(px[2] * 0.6), 255))
                    break
    save(im, "textures/item/cat_bell.png")


def gen_parrot_cracker_item(van):
    rng = random.Random(106)
    im = Image.new("RGBA", (16, 16), TRANSPARENT)
    tan = (222, 178, 108, 255)
    tan_l = (240, 205, 140, 255)
    tan_d = (188, 140, 74, 255)
    edge = (140, 96, 44, 255)
    # round biscuit
    rect(im, 5, 2, 11, 3, tan)
    rect(im, 4, 3, 12, 4, tan)
    rect(im, 3, 4, 13, 12, tan)
    rect(im, 4, 12, 12, 13, tan)
    rect(im, 5, 13, 11, 14, tan)
    # baked shading: light upper-left, dark lower-right
    rect(im, 4, 3, 8, 7, tan_l)
    rect(im, 9, 9, 13, 12, tan_d)
    rect(im, 6, 12, 11, 14, tan_d)
    # seeds pressed into it (dark + a couple of colorful millet seeds)
    seeds = [((6, 5), (92, 62, 30)), ((9, 4), (70, 48, 22)), ((11, 6), (92, 62, 30)),
             ((5, 8), (70, 48, 22)), ((8, 8), (54, 38, 18)), ((11, 10), (70, 48, 22)),
             ((6, 11), (92, 62, 30)), ((9, 12), (54, 38, 18)),
             ((7, 6), (168, 44, 40)), ((10, 8), (94, 128, 52)),
             ((4, 6), (168, 148, 96)), ((8, 10), (168, 148, 96))]
    for (x, y), c in seeds:
        im.putpixel((x, y), c + (255,))
    # crumb edge outline
    for y in range(16):
        for x in range(16):
            px = im.getpixel((x, y))
            if px[3] == 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 16 and 0 <= ny < 16) or im.getpixel((nx, ny))[3] == 0:
                    im.putpixel((x, y), edge)
                    break
    # nibbled corner
    im.putpixel((11, 3), TRANSPARENT)
    im.putpixel((12, 4), TRANSPARENT)
    save(im, "textures/item/parrot_cracker.png")


# ==========================================================================
# ARMOR LAYER (64x32)
# ==========================================================================

def gen_mining_hat_armor(van):
    iron = Image.open(os.path.join(van, "models/armor/iron_layer_1.png")).convert("RGBA")
    im = Image.new("RGBA", iron.size, TRANSPARENT)
    # keep only the helmet region (head box at 0,0..32,16), recolored yellow
    tone = (252, 202, 44)
    pivot = 190.0
    for y in range(0, 16):
        for x in range(0, 32):
            px = iron.getpixel((x, y))
            if px[3] == 0:
                continue
            g = lum(px) / pivot
            im.putpixel((x, y), (clamp(tone[0] * g), clamp(tone[1] * g),
                                 clamp(tone[2] * g), px[3]))
    # thin light-gray brim along the helmet's lower edge (side faces)
    for x in range(0, 32):
        for y in range(15, 7, -1):
            if im.getpixel((x, y))[3] > 0:
                im.putpixel((x, y), (203, 203, 209, 255))
                break
    # white lamp square on the front face (front face = 8..16 x 8..16)
    rect(im, 11, 9, 14, 12, (255, 255, 255, 255))
    im.putpixel((11, 9), (255, 255, 214, 255))
    # dark casing ring around the lamp
    for (x, y) in [(10, 9), (10, 10), (10, 11), (14, 9), (14, 10), (14, 11),
                   (11, 8), (12, 8), (13, 8), (11, 12), (12, 12), (13, 12)]:
        im.putpixel((x, y), (96, 96, 104, 255))
    save(im, "textures/models/armor/mining_hat_layer_1.png")


# ==========================================================================
# ENTITY TEXTURES
# ==========================================================================

MUSHROOM_TONE = (152, 136, 150)   # mycelium purple-grey
MUSHROOM_PIVOT = 100.0
CAP_RED = (188, 42, 40, 255)
CAP_RED_D = (138, 28, 28, 255)
CAP_WHITE = (244, 240, 232, 255)


def _paint_mushroom_caps(im, rng):
    """Red-with-white-dots caps in the hat region + one on the shoulder."""
    # big cap sitting on the head: whole hat top face...
    x0, y0, x1, y1 = HAT_TOP
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-8, 4)
            im.putpixel((x, y), (clamp(CAP_RED[0] + d), clamp(CAP_RED[1] + d // 2),
                                 clamp(CAP_RED[2] + d // 2), 255))
    for (x, y) in [(42, 2), (45, 4), (41, 5), (44, 6), (46, 1)]:
        im.putpixel((x, y), CAP_WHITE)
    # ...plus the cap lip on the upper rows of every hat side face
    for y in range(8, 11):
        for x in range(32, 64):
            if y == 10:
                im.putpixel((x, y), CAP_RED_D)
            else:
                d = rng.randint(-8, 4)
                im.putpixel((x, y), (clamp(CAP_RED[0] + d),
                                     clamp(CAP_RED[1] + d // 2),
                                     clamp(CAP_RED[2] + d // 2), 255))
    for (x, y) in [(35, 8), (43, 9), (50, 8), (59, 9), (46, 8)]:
        im.putpixel((x, y), CAP_WHITE)
    # a sprout on the back of the head (hat back face, below the lip)
    rect(im, 58, 12, 61, 14, CAP_RED)
    im.putpixel((59, 12), CAP_WHITE)
    rect(im, 59, 14, 60, 15, (216, 205, 190, 255))  # little stem
    # small cap on the shoulder (arm top face; mirrored onto both arms)
    ax0, ay0 = ARM_TOP[0], ARM_TOP[1]
    rect(im, ax0, ay0, ax0 + 3, ay0 + 3, CAP_RED)
    im.putpixel((ax0 + 2, ay0 + 2), CAP_RED_D)
    im.putpixel((ax0 + 1, ay0 + 1), CAP_WHITE)


def gen_mushroom_villager_type(van):
    rng = random.Random(201)
    src = os.path.join(van, "entity/villager/type/plains.png")
    if not os.path.exists(src):
        src = os.path.join(van, "entity/villager/villager.png")
    im = Image.open(src).convert("RGBA").copy()
    remap(im, (0, 0, 64, 64), MUSHROOM_TONE, MUSHROOM_PIVOT)
    _paint_mushroom_caps(im, rng)
    save(im, "textures/entity/villager/type/mushroom.png")


def gen_mushroom_zombie_villager_type(van):
    rng = random.Random(202)
    src = os.path.join(van, "entity/zombie_villager/type/plains.png")
    im = Image.open(src).convert("RGBA").copy()
    remap(im, (0, 0, 64, 64), MUSHROOM_TONE, MUSHROOM_PIVOT)
    _paint_mushroom_caps(im, rng)
    save(im, "textures/entity/zombie_villager/type/mushroom.png")


# ---- miner profession overlay --------------------------------------------

HAT_YELLOW = (247, 198, 35, 255)
HAT_YELLOW_L = (255, 228, 100, 255)
HAT_YELLOW_D = (198, 150, 22, 255)
BRIM_GREY = (206, 206, 212, 255)
APRON_BROWN = (118, 82, 48, 255)
APRON_BROWN_D = (88, 60, 34, 255)
APRON_BROWN_L = (142, 102, 62, 255)


def _paint_hardhat(im, rng):
    # hat top face: yellow dome with ridge + highlight
    x0, y0, x1, y1 = HAT_TOP
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-6, 6)
            im.putpixel((x, y), (clamp(HAT_YELLOW[0] + d), clamp(HAT_YELLOW[1] + d),
                                 clamp(HAT_YELLOW[2] + d // 2), 255))
    rect(im, 43, 0, 45, 8, HAT_YELLOW_L)          # center ridge
    rect(im, 46, 5, 48, 8, HAT_YELLOW_D)
    im.putpixel((40, 0), HAT_YELLOW_D)
    im.putpixel((47, 0), HAT_YELLOW_D)
    # hat side faces: shell rows y8..11, light grey brim row y12
    for y in range(8, 12):
        for x in range(32, 64):
            if y == 11:
                im.putpixel((x, y), HAT_YELLOW_D)
            else:
                d = rng.randint(-6, 6)
                im.putpixel((x, y), (clamp(HAT_YELLOW[0] + d),
                                     clamp(HAT_YELLOW[1] + d),
                                     clamp(HAT_YELLOW[2] + d // 2), 255))
    for x in range(32, 64):
        im.putpixel((x, 12), BRIM_GREY)
    # lamp on the front face: white lens with dark casing
    rect(im, 43, 8, 45, 11, (104, 104, 112, 255))
    rect(im, 43, 9, 45, 11, (255, 255, 255, 255))
    im.putpixel((43, 9), (255, 255, 214, 255))


def _paint_miner_apron(im, rng):
    # body front: leather apron bib + skirt with straps over the shoulders
    rect(im, 23, 28, 29, 38, APRON_BROWN)
    for y in range(28, 38):
        for x in range(23, 29):
            d = rng.randint(-6, 6)
            px = im.getpixel((x, y))
            im.putpixel((x, y), (clamp(px[0] + d), clamp(px[1] + d),
                                 clamp(px[2] + d), 255))
    rect(im, 23, 32, 29, 33, APRON_BROWN_D)        # waist seam
    rect(im, 24, 34, 28, 37, APRON_BROWN_L)        # front pocket
    rect(im, 24, 34, 28, 35, APRON_BROWN_D)
    # straps up and over the shoulders
    for x in (24, 27):
        rect(im, x, 26, x + 1, 28, APRON_BROWN_D)
        rect(im, x, 21, x + 1, 26, APRON_BROWN_D)  # body top face (shoulders)
    # crossed straps on the back
    for i in range(6):
        im.putpixel((37 + i, 27 + i), APRON_BROWN_D)
        im.putpixel((42 - i, 27 + i), APRON_BROWN_D)
    rect(im, 36, 33, 44, 34, APRON_BROWN_D)        # back belt
    # jacket layer copy (renders slightly inflated over the robe)
    rect(im, 7, 46, 13, 56, APRON_BROWN)
    for y in range(46, 56):
        for x in range(7, 13):
            d = rng.randint(-6, 6)
            px = im.getpixel((x, y))
            im.putpixel((x, y), (clamp(px[0] + d), clamp(px[1] + d),
                                 clamp(px[2] + d), 255))
    rect(im, 7, 50, 13, 51, APRON_BROWN_D)
    rect(im, 8, 52, 12, 55, APRON_BROWN_L)
    rect(im, 8, 52, 12, 53, APRON_BROWN_D)
    for x in (8, 11):
        rect(im, x, 44, x + 1, 46, APRON_BROWN_D)
        rect(im, x, 39, x + 1, 44, APRON_BROWN_D)  # jacket top face


def gen_miner_profession(van, zombie):
    rng = random.Random(204 if zombie else 203)
    im = Image.new("RGBA", (64, 64), TRANSPARENT)
    _paint_hardhat(im, rng)
    _paint_miner_apron(im, rng)
    if zombie:
        # tattered hem: chip a few pixels off the apron bottom
        for x in (24, 27, 9, 12, 38, 41):
            if x < 16:
                im.putpixel((x, 55), TRANSPARENT)
            else:
                im.putpixel((x, 37), TRANSPARENT)
        save(im, "textures/entity/zombie_villager/profession/miner.png")
    else:
        save(im, "textures/entity/villager/profession/miner.png")


# ---- tavern keeper profession overlay ------------------------------------

VEST_RED = (154, 44, 40, 255)
VEST_RED_D = (112, 30, 28, 255)
APRON_WHITE = (233, 229, 219, 255)
APRON_WHITE_D = (198, 192, 178, 255)
CAP_MAROON = (96, 34, 38, 255)
CAP_MAROON_D = (70, 24, 28, 255)


def gen_tavern_keeper_profession(van, zombie):
    rng = random.Random(206 if zombie else 205)
    im = Image.new("RGBA", (64, 64), TRANSPARENT)
    # small cap: hat top face + two side rows
    x0, y0, x1, y1 = HAT_TOP
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-5, 5)
            im.putpixel((x, y), (clamp(CAP_MAROON[0] + d), clamp(CAP_MAROON[1] + d),
                                 clamp(CAP_MAROON[2] + d), 255))
    for x in range(32, 64):
        im.putpixel((x, 8), CAP_MAROON)
        im.putpixel((x, 9), CAP_MAROON_D)
    # warm red vest: body front top, sides and back
    rect(im, 22, 26, 30, 32, VEST_RED)
    rect(im, 22, 26, 30, 27, VEST_RED_D)
    rect(im, 25, 26, 27, 29, TRANSPARENT)          # open collar V
    im.putpixel((25, 26), VEST_RED_D)
    im.putpixel((26, 26), VEST_RED_D)
    rect(im, 16, 26, 22, 33, VEST_RED)             # body right
    rect(im, 30, 26, 36, 33, VEST_RED)             # body left
    rect(im, 36, 26, 44, 33, VEST_RED)             # body back
    rect(im, 36, 32, 44, 33, VEST_RED_D)
    rect(im, 22, 20, 30, 26, VEST_RED)             # shoulders (body top)
    rect(im, 30, 20, 38, 26, VEST_RED_D)           # body bottom face
    # vest buttons
    im.putpixel((24, 28), (240, 214, 130, 255))
    im.putpixel((24, 30), (240, 214, 130, 255))
    # white apron: lower body front + ties on the sides
    for y in range(32, 38):
        for x in range(23, 29):
            d = rng.randint(-5, 5)
            im.putpixel((x, y), (clamp(APRON_WHITE[0] + d), clamp(APRON_WHITE[1] + d),
                                 clamp(APRON_WHITE[2] + d), 255))
    rect(im, 23, 32, 29, 33, APRON_WHITE_D)
    rect(im, 16, 32, 18, 33, APRON_WHITE_D)        # tie, right side
    rect(im, 34, 32, 36, 33, APRON_WHITE_D)        # tie, left side
    # jacket layer: vest top + white apron skirt
    rect(im, 6, 44, 14, 50, VEST_RED)
    rect(im, 20, 44, 28, 50, VEST_RED)             # jacket back
    rect(im, 0, 44, 6, 50, VEST_RED)               # jacket right
    rect(im, 14, 44, 20, 50, VEST_RED)             # jacket left
    rect(im, 6, 38, 14, 44, VEST_RED)              # jacket top
    rect(im, 9, 44, 11, 46, TRANSPARENT)           # collar V
    for y in range(50, 56):
        for x in range(7, 13):
            d = rng.randint(-5, 5)
            im.putpixel((x, y), (clamp(APRON_WHITE[0] + d), clamp(APRON_WHITE[1] + d),
                                 clamp(APRON_WHITE[2] + d), 255))
    rect(im, 7, 50, 13, 51, APRON_WHITE_D)
    if zombie:
        for x, y in ((8, 55), (11, 55), (24, 37), (27, 37)):
            im.putpixel((x, y), TRANSPARENT)
        save(im, "textures/entity/zombie_villager/profession/tavern_keeper.png")
    else:
        save(im, "textures/entity/villager/profession/tavern_keeper.png")


# ---- mercenary -------------------------------------------------------------

STEEL = (122, 126, 134)
STEEL_D = (84, 88, 96)
STEEL_L = (168, 172, 182)
LEATHER = (126, 86, 48)
HEADBAND = (158, 34, 32, 255)
HEADBAND_D = (116, 22, 22, 255)


def _steel_fill(im, box, rng):
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-7, 7)
            im.putpixel((x, y), (clamp(STEEL[0] + d), clamp(STEEL[1] + d),
                                 clamp(STEEL[2] + d), 255))


def gen_mercenary(van):
    rng = random.Random(207)
    im = Image.open(os.path.join(van, "entity/villager/villager.png")).convert("RGBA").copy()
    # iron-grey cuirass over the whole torso (body box)
    _steel_fill(im, BODY_ALL, rng)
    rect(im, 22, 26, 30, 27, tuple(STEEL_D) + (255,))       # neck rim
    rect(im, 25, 27, 27, 34, tuple(STEEL_L) + (255,))       # center ridge
    for (x, y) in [(23, 28), (28, 28), (23, 33), (28, 33),
                   (38, 28), (42, 28), (38, 33), (42, 33)]:  # rivets
        im.putpixel((x, y), tuple(STEEL_D) + (255,))
    # belt with buckle
    rect(im, 16, 35, 44, 37, (74, 52, 30, 255))
    rect(im, 25, 35, 27, 37, (214, 178, 84, 255))
    # cuirass also on the (normally empty) jacket layer so it reads as armor
    _steel_fill(im, (6, 38, 14, 44), rng)                    # jacket top
    _steel_fill(im, (0, 44, 28, 56), rng)                    # jacket sides
    rect(im, 0, 55, 28, 56, tuple(STEEL_D) + (255,))         # tasset rim
    rect(im, 9, 45, 11, 52, tuple(STEEL_L) + (255,))
    rect(im, 0, 50, 28, 51, (74, 52, 30, 255))               # belt
    rect(im, 9, 50, 11, 51, (214, 178, 84, 255))
    # leather-brown arms (sleeves); hands stay skin
    remap(im, ARM, LEATHER, 145)
    for y in range(ARMS_CROSS[1], ARMS_CROSS[3]):
        for x in range(ARMS_CROSS[0], ARMS_CROSS[2]):
            fx0, fy0, fx1, fy1 = ARMS_CROSS_FRONT
            bx0, by0, bx1, by1 = ARMS_CROSS_BOTTOM
            if (fx0 <= x < fx1 and fy0 <= y < fy1) or (bx0 <= x < bx1 and by0 <= y < by1):
                continue  # hands keep their skin tone
            px = im.getpixel((x, y))
            if px[3] == 0:
                continue
            g = lum(px) / 145.0
            im.putpixel((x, y), (clamp(LEATHER[0] * g), clamp(LEATHER[1] * g),
                                 clamp(LEATHER[2] * g), 255))
    # red headband across the brow (all four head side faces)
    for x in range(0, 32):
        im.putpixel((x, 10), HEADBAND)
        im.putpixel((x, 11), HEADBAND_D)
    rect(im, 27, 12, 29, 14, HEADBAND)                       # knot on the back
    im.putpixel((28, 14), HEADBAND_D)
    # sturdy dark trousers + iron-toed boots
    remap(im, LEGS, (72, 66, 58), 150)
    rect(im, 0, 35, 16, 38, (60, 62, 68, 255))
    rect(im, 0, 35, 16, 36, (92, 96, 104, 255))
    save(im, "textures/entity/mercenary.png")


# ---- the collector ---------------------------------------------------------

ILLAGER_SKIN = (142, 147, 147)
ILLAGER_PIVOT = 149.0
NAVY = (34, 40, 68)
NAVY_L = (52, 60, 96)
NAVY_D = (22, 26, 46)
GOLD_TRIM = (206, 168, 74, 255)


def _navy_fill(im, box, rng):
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = rng.randint(-5, 5)
            im.putpixel((x, y), (clamp(NAVY[0] + d), clamp(NAVY[1] + d),
                                 clamp(NAVY[2] + d + 2), 255))


def gen_collector(van):
    rng = random.Random(208)
    im = Image.open(os.path.join(van, "entity/villager/villager.png")).convert("RGBA").copy()
    # illager-grey skin on head + nose (eyes/mouth pixels are not skin-toned)
    remap(im, HEAD_ALL, ILLAGER_SKIN, ILLAGER_PIVOT, pred=is_skin)
    remap(im, NOSE, ILLAGER_SKIN, ILLAGER_PIVOT, pred=is_skin)
    # single joined heavy brow (thicken the vanilla brow row upward)
    for x in range(9, 15):
        im.putpixel((x, 12), (58, 54, 50, 255))
        im.putpixel((x, 13), (40, 37, 34, 255))
    # long dark-navy coat with gold trim: torso
    _navy_fill(im, BODY_ALL, rng)
    rect(im, 22, 26, 30, 27, GOLD_TRIM)              # collar
    rect(im, 16, 37, 44, 38, GOLD_TRIM)              # waist trim
    rect(im, 25, 27, 26, 37, tuple(NAVY_D) + (255,))  # coat opening
    for y in (28, 31, 34):                            # gold buttons
        im.putpixel((26, y), GOLD_TRIM[:3] + (255,))
    rect(im, 22, 20, 30, 26, tuple(NAVY_L) + (255,))  # shoulders
    # coat skirt on the jacket layer
    _navy_fill(im, (6, 38, 14, 44), rng)
    _navy_fill(im, (0, 44, 28, 56), rng)
    rect(im, 0, 55, 28, 56, GOLD_TRIM)                # hem trim
    rect(im, 10, 44, 11, 55, tuple(NAVY_D) + (255,))  # front opening
    # navy sleeves with gold cuffs; hands become illager-grey
    _navy_fill(im, ARM, rng)
    rect(im, 44, 33, 60, 34, GOLD_TRIM)               # cuff ring
    for y in range(ARMS_CROSS[1], ARMS_CROSS[3]):
        for x in range(ARMS_CROSS[0], ARMS_CROSS[2]):
            px = im.getpixel((x, y))
            if px[3] == 0:
                continue
            fx0, fy0, fx1, fy1 = ARMS_CROSS_FRONT
            bx0, by0, bx1, by1 = ARMS_CROSS_BOTTOM
            if (fx0 <= x < fx1 and fy0 <= y < fy1) or (bx0 <= x < bx1 and by0 <= y < by1):
                if is_skin(px):  # hands -> grey
                    g = lum(px) / ILLAGER_PIVOT
                    im.putpixel((x, y), (clamp(ILLAGER_SKIN[0] * g),
                                         clamp(ILLAGER_SKIN[1] * g),
                                         clamp(ILLAGER_SKIN[2] * g), 255))
                continue
            d = rng.randint(-5, 5)
            im.putpixel((x, y), (clamp(NAVY[0] + d), clamp(NAVY[1] + d),
                                 clamp(NAVY[2] + d + 2), 255))
    # dark trousers and boots under the coat
    remap(im, LEGS, (46, 48, 56), 150)
    rect(im, 0, 35, 16, 38, (26, 26, 30, 255))
    save(im, "textures/entity/collector.png")


# ==========================================================================
# MOD ICON (128x128; drawn at 32x32, scaled 4x)
# ==========================================================================

def gen_icon(van):
    rng = random.Random(209)
    art = Image.new("RGBA", (32, 32))
    # cave air gradient
    for y in range(32):
        for x in range(32):
            t = y / 31.0
            d = rng.randint(-4, 4)
            art.putpixel((x, y), (clamp(16 + 8 * t + d), clamp(15 + 7 * t + d),
                                  clamp(24 + 9 * t + d), 255))
    # rough stone ring around the cavern
    stone = [(96, 96, 100), (110, 110, 114), (84, 84, 90), (122, 122, 126)]
    def stonepx(x, y, extra=0):
        c = stone[(x * 5 + y * 3 + (x * y) % 7) % 4]
        d = rng.randint(-8, 8) + extra
        art.putpixel((x, y), (clamp(c[0] + d), clamp(c[1] + d), clamp(c[2] + d), 255))
    for x in range(32):
        for y in range(32):
            edge = min(x, y, 31 - x)
            if edge < 3 or y > 28:
                stonepx(x, y)
    # ceiling stalactites
    for (sx, ln) in [(6, 3), (12, 2), (19, 4), (26, 2)]:
        for i in range(ln):
            stonepx(sx, 3 + i, extra=-12 - 4 * i)
        stonepx(sx, 3 + ln, extra=-30)
    # cave floor
    for x in range(3, 29):
        for y in range(27, 29):
            stonepx(x, y, extra=-20)
    # house silhouette
    wall = (33, 30, 40, 255)
    roof = (48, 40, 52, 255)
    for y in range(15, 27):                       # walls
        for x in range(9, 24):
            art.putpixel((x, y), wall)
    for i in range(7):                            # gable roof
        for x in range(9 + i, 24 - i):
            art.putpixel((x, 15 - i), roof if i < 6 else (60, 50, 62, 255))
    for i in range(6):                            # roof edge highlight
        art.putpixel((9 + i, 15 - i), (72, 60, 74, 255))
        art.putpixel((23 - i, 15 - i), (72, 60, 74, 255))
    # glowing windows
    win = (255, 186, 74, 255)
    win_core = (255, 232, 150, 255)
    for (wx, wy) in [(11, 18), (19, 18)]:
        rect(art, wx, wy, wx + 3, wy + 3, win)
        art.putpixel((wx + 1, wy + 1), win_core)
        for (dx, dy) in ((-1, 0), (3, 0), (0, -1), (0, 3), (2, -1), (2, 3), (-1, 2), (3, 2)):
            x, y = wx + dx + (1 if dx in (0, 2) else 0), wy + dy + (1 if dy in (0, 2) else 0)
            px = art.getpixel((x, y))
            art.putpixel((x, y), (clamp(px[0] + 60), clamp(px[1] + 38),
                                  clamp(px[2] + 8), 255))
    # door
    rect(art, 15, 21, 18, 27, (22, 20, 28, 255))
    rect(art, 15, 21, 18, 22, (70, 56, 40, 255))
    art.putpixel((16, 24), (150, 120, 60, 255))
    # hanging lantern
    chain_x = 27
    for y in range(3, 8):
        art.putpixel((chain_x, y), (70, 70, 76, 255))
    rect(art, chain_x - 1, 8, chain_x + 2, 12, (60, 56, 50, 255))
    rect(art, chain_x - 1, 9, chain_x + 2, 11, (255, 200, 90, 255))
    art.putpixel((chain_x, 9), (255, 240, 170, 255))
    art.putpixel((chain_x, 10), (255, 240, 170, 255))
    for (x, y) in [(chain_x - 2, 9), (chain_x + 2, 10), (chain_x, 12), (chain_x - 2, 11)]:
        px = art.getpixel((x, y))
        art.putpixel((x, y), (clamp(px[0] + 70), clamp(px[1] + 48), clamp(px[2] + 10), 255))
    # warm light pooling on the floor by the door
    for x in range(14, 20):
        px = art.getpixel((x, 27))
        art.putpixel((x, 27), (clamp(px[0] + 42), clamp(px[1] + 26), clamp(px[2] + 4), 255))
    icon = art.resize((128, 128), Image.NEAREST)
    icon.save(os.path.join(ASSETS, "icon.png"), optimize=True)
    print("wrote assets/undergroundvillages/icon.png")


# ==========================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla", default=DEFAULT_VANILLA,
                    help="path to vanilla assets/minecraft/textures")
    args = ap.parse_args()
    van = args.vanilla
    if not os.path.isdir(van):
        sys.exit(f"vanilla texture dir not found: {van}")

    os.makedirs(ASSETS, exist_ok=True)

    gen_prospecting_table_top(van)
    gen_prospecting_table_side(van)
    gen_prospecting_table_bottom(van)
    gen_tavern_hearth_side(van)
    gen_tavern_hearth_top(van)

    gen_mining_hat_item(van)
    gen_wolf_whistle_item(van)
    gen_cat_bell_item(van)
    gen_parrot_cracker_item(van)

    gen_mining_hat_armor(van)

    gen_mushroom_villager_type(van)
    gen_mushroom_zombie_villager_type(van)
    gen_miner_profession(van, zombie=False)
    gen_miner_profession(van, zombie=True)
    gen_tavern_keeper_profession(van, zombie=False)
    gen_tavern_keeper_profession(van, zombie=True)
    gen_mercenary(van)
    gen_collector(van)

    gen_icon(van)
    print("done.")


if __name__ == "__main__":
    main()
