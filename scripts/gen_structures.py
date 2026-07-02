#!/usr/bin/env python3
"""Generate every Underground Villages structure template (.nbt).

Deterministic, stdlib-only. Templates are written to
  src/main/resources/data/undergroundvillages/structure/

Usage:
  python3 scripts/gen_structures.py            # (re)write templates in place
  python3 scripts/gen_structures.py --check    # regenerate into a temp dir and
                                               # byte-compare with committed files

Template NBT shape (matches vanilla 1.21.1 structure templates):
  root compound (name ""):
    size:       TAG_List<TAG_Int> [x, y, z]
    entities:   TAG_List<TAG_Compound {pos: List<Double>, blockPos: List<Int>, nbt}>
    blocks:     TAG_List<TAG_Compound {pos: [x,y,z], state: Int, nbt?: Compound}>
    palette:    TAG_List<TAG_Compound {Properties?: Compound<str,str>, Name: str}>
    DataVersion: TAG_Int = 3955

Every position inside the box has a block entry (air included): the templates
carve their own caverns out of solid rock.
"""

import argparse
import gzip
import io
import random
import struct
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DATA_VERSION = 3955
REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "src/main/resources/data/undergroundvillages/structure"

# ---------------------------------------------------------------------------
# Minimal NBT writer (big-endian, gzipped, byte-reproducible).
#
# Value model:
#   ("B", n) -> TAG_Byte      ("S", n) -> TAG_Short   int / ("I", n) -> TAG_Int
#   ("L", n) -> TAG_Long      ("F", x) -> TAG_Float   ("D", x) -> TAG_Double
#   str -> TAG_String   list -> TAG_List (homogeneous)   dict -> TAG_Compound
# Compounds keep insertion order; all construction below is deterministic.
# ---------------------------------------------------------------------------

_TUPLE_IDS = {"B": 1, "S": 2, "I": 3, "L": 4, "F": 5, "D": 6}


def _tag_id(v):
    if isinstance(v, bool):
        raise TypeError("use ('B', 0/1) for booleans")
    if isinstance(v, tuple):
        return _TUPLE_IDS[v[0]]
    if isinstance(v, int):
        return 3
    if isinstance(v, str):
        return 8
    if isinstance(v, list):
        return 9
    if isinstance(v, dict):
        return 10
    raise TypeError(f"unsupported NBT value: {v!r}")


def _write_str(out: bytearray, s: str) -> None:
    b = s.encode("utf-8")
    out += struct.pack(">H", len(b))
    out += b


def _write_payload(out: bytearray, v) -> None:
    tid = _tag_id(v)
    if tid == 1:
        out += struct.pack(">b", v[1])
    elif tid == 2:
        out += struct.pack(">h", v[1])
    elif tid == 3:
        out += struct.pack(">i", v[1] if isinstance(v, tuple) else v)
    elif tid == 4:
        out += struct.pack(">q", v[1])
    elif tid == 5:
        out += struct.pack(">f", v[1])
    elif tid == 6:
        out += struct.pack(">d", v[1])
    elif tid == 8:
        _write_str(out, v)
    elif tid == 9:
        ids = {_tag_id(item) for item in v}
        if len(ids) > 1:
            raise TypeError(f"heterogeneous NBT list: {v!r}")
        elem = ids.pop() if v else 0
        out.append(elem)
        out += struct.pack(">i", len(v))
        for item in v:
            _write_payload(out, item)
    elif tid == 10:
        for key, val in v.items():
            out.append(_tag_id(val))
            _write_str(out, key)
            _write_payload(out, val)
        out.append(0)
    else:  # pragma: no cover
        raise AssertionError(tid)


def nbt_bytes(root: dict) -> bytes:
    raw = bytearray()
    raw.append(10)
    _write_str(raw, "")
    _write_payload(raw, root)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(bytes(raw))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------

AIR = "minecraft:air"
EMPTY = "minecraft:empty"
J_STREET = "undergroundvillages:street"
J_HOUSE = "undergroundvillages:house"


class T:
    """A structure template: a fully-filled box of blocks plus entities."""

    def __init__(self, sx: int, sy: int, sz: int):
        self.size = (sx, sy, sz)
        self.blocks = {}  # (x,y,z) -> (name, props-tuple|None, nbt-dict|None)
        self.entities = []

    def set(self, x, y, z, name, props=None, nbt=None):
        sx, sy, sz = self.size
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            raise ValueError(f"out of bounds: {(x, y, z)} in {self.size}")
        key = tuple(sorted(props.items())) if props else None
        self.blocks[(x, y, z)] = (name, key, nbt)

    def fill(self, x1, y1, z1, x2, y2, z2, name, props=None, nbt=None):
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    self.set(x, y, z, name, props, nbt)

    def jigsaw(self, x, y, z, orientation, name, target, pool, final_state,
               joint="aligned"):
        self.set(x, y, z, "minecraft:jigsaw", {"orientation": orientation}, nbt={
            "name": name,
            "target": target,
            "pool": pool,
            "final_state": final_state,
            "joint": joint,
            "placement_priority": ("I", 0),
            "selection_priority": ("I", 0),
            "id": "minecraft:jigsaw",
        })

    def entity(self, x, y, z, nbt):
        self.entities.append({
            "pos": [("D", x + 0.5), ("D", float(y)), ("D", z + 0.5)],
            "blockPos": [x, y, z],
            "nbt": nbt,
        })

    def to_nbt(self) -> bytes:
        sx, sy, sz = self.size
        if len(self.blocks) != sx * sy * sz:
            raise AssertionError(
                f"template not fully covered: {len(self.blocks)} != {sx * sy * sz}")
        palette_index = {}
        palette = []
        blocks = []
        for pos in sorted(self.blocks):
            name, props, nbt = self.blocks[pos]
            key = (name, props)
            idx = palette_index.get(key)
            if idx is None:
                idx = len(palette)
                palette_index[key] = idx
                entry = {}
                if props:
                    entry["Properties"] = {k: v for k, v in props}
                entry["Name"] = name
                palette.append(entry)
            block = {"pos": list(pos), "state": idx}
            if nbt is not None:
                block["nbt"] = nbt
            blocks.append(block)
        return nbt_bytes({
            "size": list(self.size),
            "entities": self.entities,
            "blocks": blocks,
            "palette": palette,
            "DataVersion": DATA_VERSION,
        })


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Style:
    village: str      # pool folder, e.g. "mining_village"
    rock: str         # native rock the pieces are carved from
    path: str         # street floor block
    face: str         # facade / plug wall block
    plank: str        # interior floors, platforms
    log: str | None   # beam/frame material (needs axis property)
    fence: str
    door: str
    light: str | None  # lantern block, or None for unlit (zombie)
    rails: bool
    decay: bool
    shroom: bool


MINING = Style("mining_village", "minecraft:stone", "minecraft:cobblestone",
               "minecraft:cobblestone", "minecraft:oak_planks", "minecraft:oak_log",
               "minecraft:oak_fence", "minecraft:oak_door", "minecraft:lantern",
               rails=True, decay=False, shroom=False)
ZOMBIE = Style("zombie_village", "minecraft:stone", "minecraft:cobblestone",
               "minecraft:cobblestone", "minecraft:oak_planks", "minecraft:oak_log",
               "minecraft:oak_fence", "minecraft:oak_door", None,
               rails=True, decay=True, shroom=False)
MUSHROOM = Style("mushroom_village", "minecraft:stone", "minecraft:mycelium",
                 "minecraft:mushroom_stem", "minecraft:mycelium", None,
                 "minecraft:oak_fence", "minecraft:oak_door", None,
                 rails=False, decay=False, shroom=True)
ILLAGER = Style("illager_village", "minecraft:deepslate", "minecraft:cobbled_deepslate",
                "minecraft:cobbled_deepslate", "minecraft:dark_oak_planks",
                "minecraft:dark_oak_log", "minecraft:dark_oak_fence",
                "minecraft:dark_oak_door", "minecraft:soul_lantern",
                rails=False, decay=False, shroom=False)

SHROOMLIGHT = "minecraft:shroomlight"
STEM = "minecraft:mushroom_stem"


def streets_pool(st: Style) -> str:
    return f"undergroundvillages:{st.village}/streets"


def houses_pool(st: Style) -> str:
    return f"undergroundvillages:{st.village}/houses"


def door(t: T, x, y, z, facing, block):
    common = {"facing": facing, "hinge": "left", "open": "false", "powered": "false"}
    t.set(x, y, z, block, dict(common, half="lower"))
    t.set(x, y + 1, z, block, dict(common, half="upper"))


def bed(t: T, x, y, z, facing, color):
    dx, dz = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[facing]
    block = f"minecraft:{color}_bed"
    be = {"id": "minecraft:bed"}
    t.set(x, y, z, block, {"facing": facing, "part": "foot"}, nbt=dict(be))
    t.set(x + dx, y, z + dz, block, {"facing": facing, "part": "head"}, nbt=dict(be))


def wall_torch(t: T, x, y, z, facing):
    t.set(x, y, z, "minecraft:wall_torch", {"facing": facing})


def lantern_post(t: T, st: Style, x, y, z):
    """Two fence blocks with a lantern on top, base at (x, y, z)."""
    t.fill(x, y, z, x, y + 1, z, st.fence)
    t.set(x, y + 2, z, st.light, {"hanging": "false"})


def hanging_light(t: T, st: Style, x, y, z):
    if st.light:
        t.set(x, y, z, st.light, {"hanging": "true"})


def loot_chest(t: T, x, y, z, facing, table):
    t.set(x, y, z, "minecraft:chest", {"facing": facing, "type": "single"},
          nbt={"id": "minecraft:chest", "LootTable": table})


def villager_nbt(vtype, profession):
    return {
        "id": "minecraft:villager",
        "VillagerData": {"level": ("I", 2), "profession": profession, "type": vtype},
        "Xp": ("I", 10),
        "PersistenceRequired": ("B", 1),
    }


def zombie_villager_nbt(profession):
    return {
        "id": "minecraft:zombie_villager",
        "VillagerData": {"level": ("I", 2), "profession": profession,
                         "type": "minecraft:plains"},
        "IsBaby": ("B", 0),
        "PersistenceRequired": ("B", 1),
    }


def mob_nbt(eid):
    return {"id": eid, "PersistenceRequired": ("B", 1)}


MINER = "undergroundvillages:miner"
NONE = "minecraft:none"
MINESHAFT_LOOT = "minecraft:chests/abandoned_mineshaft"


def house_folk(t: T, st: Style, spots, profession=MINER):
    """Populate a mining-family house: villagers, or zombie villagers if decayed.

    Decayed houses get one extra inhabitant (2-3 zombies per house)."""
    if st.decay:
        for i, (x, y, z) in enumerate(spots):
            prof = profession if i == 0 else NONE
            t.entity(x, y, z, zombie_villager_nbt(prof))
    else:
        for x, y, z in spots[:-1]:
            t.entity(x, y, z, villager_nbt("minecraft:plains", profession))


# ---------------------------------------------------------------------------
# Streets & terminator (shared geometry, styled per village)
#
# Tunnel cross-section, identical everywhere: 7 wide x 7 high;
# floor row y=0 (path), air x=1..5 / y=1..5, walls x=0/x=6, ceiling y=6.
# Street connector jigsaws sit in the floor at the mouth center.
# ---------------------------------------------------------------------------

def street_straight(st: Style) -> T:
    t = T(7, 7, 12)
    t.fill(0, 0, 0, 6, 6, 11, st.rock)
    t.fill(1, 1, 0, 5, 5, 11, AIR)
    t.fill(1, 0, 0, 5, 0, 11, st.path)

    # timber frames + lighting
    if st.log:
        for z in (2, 9):
            if st.decay and z == 9:  # collapsed frame: only a stump remains
                t.fill(1, 1, z, 1, 2, z, st.log, {"axis": "y"})
                continue
            t.fill(1, 1, z, 1, 4, z, st.log, {"axis": "y"})
            t.fill(5, 1, z, 5, 4, z, st.log, {"axis": "y"})
            t.fill(1, 5, z, 5, 5, z, st.log, {"axis": "x"})
            hanging_light(t, st, 3, 4, z)
    if st.shroom:
        for z in (2, 9):
            t.fill(1, 1, z, 1, 4, z, STEM)
            t.fill(5, 1, z, 5, 4, z, STEM)
            t.set(3, 6, z, SHROOMLIGHT)
        t.set(1, 1, 6, "minecraft:red_mushroom")
        t.set(5, 1, 3, "minecraft:brown_mushroom")

    if st.rails:
        gaps = {3, 7} if st.decay else set()
        for z in range(12):
            if z not in gaps:
                t.set(3, 1, z, "minecraft:rail", {"shape": "north_south"})

    if st.decay:
        t.set(1, 5, 1, "minecraft:cobweb")
        t.set(5, 5, 10, "minecraft:cobweb")
        t.fill(6, 1, 4, 6, 2, 5, AIR)  # breached east wall
        t.set(5, 1, 4, "minecraft:cobblestone")
        t.set(5, 1, 5, "minecraft:mossy_cobblestone")

    sp, hp = streets_pool(st), houses_pool(st)
    t.jigsaw(3, 0, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.jigsaw(3, 0, 11, "south_up", J_STREET, J_STREET, sp, st.path)
    # house sockets: door-sized openings in the side walls
    t.fill(0, 1, 3, 0, 4, 5, AIR)
    t.fill(0, 0, 3, 0, 0, 5, st.path)
    t.jigsaw(0, 0, 4, "west_up", J_HOUSE, J_HOUSE, hp, st.path)
    t.fill(6, 1, 6, 6, 4, 8, AIR)
    t.fill(6, 0, 6, 6, 0, 8, st.path)
    t.jigsaw(6, 0, 7, "east_up", J_HOUSE, J_HOUSE, hp, st.path)
    return t


def street_corner(st: Style) -> T:
    t = T(12, 7, 12)
    t.fill(0, 0, 0, 11, 6, 11, st.rock)
    t.fill(1, 1, 0, 5, 5, 10, AIR)    # north leg
    t.fill(1, 1, 6, 11, 5, 10, AIR)   # east leg
    t.fill(1, 0, 0, 5, 0, 10, st.path)
    t.fill(1, 0, 6, 11, 0, 10, st.path)

    if st.log:
        t.fill(1, 1, 2, 1, 4, 2, st.log, {"axis": "y"})
        t.fill(5, 1, 2, 5, 4, 2, st.log, {"axis": "y"})
        t.fill(1, 5, 2, 5, 5, 2, st.log, {"axis": "x"})
        hanging_light(t, st, 3, 4, 2)
        if not st.decay:
            t.fill(9, 1, 6, 9, 4, 6, st.log, {"axis": "y"})
            t.fill(9, 1, 10, 9, 4, 10, st.log, {"axis": "y"})
            t.fill(9, 5, 6, 9, 5, 10, st.log, {"axis": "z"})
            hanging_light(t, st, 9, 4, 8)
    if st.shroom:
        t.fill(1, 1, 2, 1, 4, 2, STEM)
        t.fill(5, 1, 2, 5, 4, 2, STEM)
        t.set(3, 6, 2, SHROOMLIGHT)
        t.set(8, 6, 8, SHROOMLIGHT)
        t.set(1, 1, 7, "minecraft:brown_mushroom")

    if st.rails:
        gaps = {2, 6} if st.decay else set()
        for z in range(0, 8):
            if z not in gaps:
                t.set(3, 1, z, "minecraft:rail", {"shape": "north_south"})
        t.set(3, 1, 8, "minecraft:rail", {"shape": "north_east"})
        for x in range(4, 12):
            if not (st.decay and x == 6):
                t.set(x, 1, 8, "minecraft:rail", {"shape": "east_west"})

    if st.decay:
        t.set(1, 5, 7, "minecraft:cobweb")
        t.set(10, 5, 6, "minecraft:cobweb")

    sp, hp = streets_pool(st), houses_pool(st)
    t.jigsaw(3, 0, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.jigsaw(11, 0, 8, "east_up", J_STREET, J_STREET, sp, st.path)
    # house socket on the outer west wall
    t.fill(0, 1, 2, 0, 4, 4, AIR)
    t.fill(0, 0, 2, 0, 0, 4, st.path)
    t.jigsaw(0, 0, 3, "west_up", J_HOUSE, J_HOUSE, hp, st.path)
    return t


def street_t(st: Style) -> T:
    t = T(12, 7, 12)
    t.fill(0, 0, 0, 11, 6, 11, st.rock)
    t.fill(1, 1, 0, 5, 5, 11, AIR)    # through tunnel
    t.fill(6, 1, 3, 11, 5, 7, AIR)    # east branch
    t.fill(1, 0, 0, 5, 0, 11, st.path)
    t.fill(6, 0, 3, 11, 0, 7, st.path)

    if st.log:
        for z in (1, 10):
            if st.decay and z == 10:
                t.fill(5, 1, z, 5, 3, z, st.log, {"axis": "y"})
                continue
            t.fill(1, 1, z, 1, 4, z, st.log, {"axis": "y"})
            t.fill(5, 1, z, 5, 4, z, st.log, {"axis": "y"})
            t.fill(1, 5, z, 5, 5, z, st.log, {"axis": "x"})
            hanging_light(t, st, 3, 4, z)
    if st.shroom:
        t.set(3, 6, 1, SHROOMLIGHT)
        t.set(3, 6, 10, SHROOMLIGHT)
        t.set(9, 6, 5, SHROOMLIGHT)
        t.set(1, 1, 4, "minecraft:red_mushroom")
        t.set(9, 1, 3, "minecraft:brown_mushroom")

    if st.rails:
        gaps = {4, 8} if st.decay else set()
        for z in range(12):
            if z not in gaps:
                t.set(3, 1, z, "minecraft:rail", {"shape": "north_south"})
        for x in range(4, 12):
            if not (st.decay and x == 7):
                t.set(x, 1, 5, "minecraft:rail", {"shape": "east_west"})

    if st.decay:
        t.set(1, 5, 2, "minecraft:cobweb")
        t.set(10, 5, 4, "minecraft:cobweb")

    sp, hp = streets_pool(st), houses_pool(st)
    t.jigsaw(3, 0, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.jigsaw(3, 0, 11, "south_up", J_STREET, J_STREET, sp, st.path)
    t.jigsaw(11, 0, 5, "east_up", J_STREET, J_STREET, sp, st.path)
    # house socket on the west wall, south end
    t.fill(0, 1, 8, 0, 4, 10, AIR)
    t.fill(0, 0, 8, 0, 0, 10, st.path)
    t.jigsaw(0, 0, 9, "west_up", J_HOUSE, J_HOUSE, hp, st.path)
    return t


def terminator(st: Style) -> T:
    """Solid plug matching the street cross-section. Carries two jigsaws so it
    can cap both street connectors and house sockets when used as fallback."""
    t = T(7, 7, 2)
    t.fill(0, 0, 0, 6, 6, 1, st.rock)
    t.fill(0, 0, 0, 6, 6, 0, st.face)
    t.jigsaw(3, 0, 0, "north_up", J_STREET, J_STREET, EMPTY, st.face)
    t.jigsaw(2, 0, 0, "north_up", J_HOUSE, J_HOUSE, EMPTY, st.face)
    return t


# ---------------------------------------------------------------------------
# Carved-room houses (mining / zombie / illager families)
# ---------------------------------------------------------------------------

def carved_room(st: Style, sx, sy, sz, door_z, floor=None) -> T:
    """A room carved out of rock with a built facade (x=0 plane) and a door.
    The house jigsaw sits in the floor of the doorway, pointing out (west)."""
    floor = floor or st.plank
    t = T(sx, sy, sz)
    t.fill(0, 0, 0, sx - 1, sy - 1, sz - 1, st.rock)
    t.fill(1, 1, 1, sx - 2, sy - 2, sz - 2, AIR)
    t.fill(1, 0, 1, sx - 2, 0, sz - 2, floor)
    t.fill(0, 0, 0, 0, sy - 1, sz - 1, st.face)
    if st.decay:  # zombie houses lost their doors
        t.fill(0, 1, door_z, 0, 2, door_z, AIR)
    else:
        door(t, 0, 1, door_z, "west", st.door)
    t.jigsaw(0, 0, door_z, "west_up", J_HOUSE, J_HOUSE, EMPTY, floor)
    return t


def corner_beams(t: T, st: Style, sx, sy, sz):
    for x, z in ((1, 1), (1, sz - 2), (sx - 2, 1), (sx - 2, sz - 2)):
        t.fill(x, 1, z, x, sy - 2, z, st.log, {"axis": "y"})


def room_torches(t: T, st: Style, sx, sy, sz, door_z):
    if st.decay:
        return
    wall_torch(t, 1, 3, door_z, "east")
    wall_torch(t, sx - 2, 3, door_z, "west")
    cx = sx // 2
    wall_torch(t, cx, 3, 1, "south")
    wall_torch(t, cx, 3, sz - 2, "north")


def decay_room(t: T, st: Style, sx, sy, sz):
    if not st.decay:
        return
    t.set(1, sy - 2, 1, "minecraft:cobweb")
    t.set(sx - 2, sy - 2, sz - 2, "minecraft:cobweb")
    # breached south wall with rubble spilling in
    bx = sx // 2
    t.fill(bx, 1, sz - 1, bx + 1, 2, sz - 1, AIR)
    t.set(bx, 1, sz - 2, "minecraft:cobblestone")
    t.set(bx + 1, 1, sz - 2, "minecraft:mossy_cobblestone")


def miner_house(st: Style) -> T:
    t = carved_room(st, 11, 8, 10, 4)
    corner_beams(t, st, 11, 8, 10)
    bed(t, 7, 1, 8, "east", "red")
    t.set(1, 1, 7, "undergroundvillages:prospecting_table")
    t.set(1, 1, 6, "minecraft:barrel", {"facing": "up"},
          nbt={"id": "minecraft:barrel"})
    t.set(2, 1, 8, "minecraft:crafting_table")
    room_torches(t, st, 11, 8, 10, 4)
    decay_room(t, st, 11, 8, 10)
    house_folk(t, st, [(4, 1, 4), (6, 1, 3), (3, 1, 6)])
    return t


def storage_house(st: Style) -> T:
    t = carved_room(st, 9, 7, 9, 4)
    loot_chest(t, 1, 1, 2, "east", MINESHAFT_LOOT)
    loot_chest(t, 1, 1, 6, "east", MINESHAFT_LOOT)
    t.set(7, 1, 1, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(7, 2, 1, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(4, 1, 4, "minecraft:rail", {"shape": "north_south"})
    t.entity(4, 1, 4, {"id": "minecraft:minecart"})
    room_torches(t, st, 9, 7, 9, 4)
    decay_room(t, st, 9, 7, 9)
    house_folk(t, st, [(5, 1, 6), (3, 1, 3)])
    return t


def forge_house(st: Style) -> T:
    t = carved_room(st, 9, 7, 9, 4, floor="minecraft:cobblestone")
    t.set(7, 1, 3, "minecraft:blast_furnace", {"facing": "west", "lit": "false"},
          nbt={"id": "minecraft:blast_furnace"})
    t.set(7, 1, 5, "minecraft:anvil", {"facing": "north"})
    t.set(7, 1, 7, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    room_torches(t, st, 9, 7, 9, 4)
    decay_room(t, st, 9, 7, 9)
    house_folk(t, st, [(4, 1, 4), (2, 1, 6), (6, 1, 6)])
    return t


# ---------------------------------------------------------------------------
# Mining / zombie town center: plaza with rails and a headframe over a shaft.
# Street level is y=3 so the shaft can drop below the plaza floor.
# ---------------------------------------------------------------------------

def mining_center(st: Style) -> T:
    rnd = random.Random(f"{st.village}:center")
    t = T(21, 14, 21)
    t.fill(0, 0, 0, 20, 13, 20, st.rock)
    t.fill(1, 4, 1, 19, 12, 19, AIR)

    # plaza floor: cobble cross under the rail lines, gravel-flecked stone elsewhere
    for x in range(1, 20):
        for z in range(1, 20):
            if 8 <= x <= 12 or 8 <= z <= 12:
                block = st.path
            else:
                block = "minecraft:gravel" if rnd.random() < 0.15 else st.rock
            t.set(x, 3, z, block)

    # four street mouths at plaza level
    sp = streets_pool(st)
    t.fill(8, 4, 0, 12, 8, 0, AIR)
    t.fill(8, 3, 0, 12, 3, 0, st.path)
    t.jigsaw(10, 3, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.fill(8, 4, 20, 12, 8, 20, AIR)
    t.fill(8, 3, 20, 12, 3, 20, st.path)
    t.jigsaw(10, 3, 20, "south_up", J_STREET, J_STREET, sp, st.path)
    t.fill(0, 4, 8, 0, 8, 12, AIR)
    t.fill(0, 3, 8, 0, 3, 12, st.path)
    t.jigsaw(0, 3, 10, "west_up", J_STREET, J_STREET, sp, st.path)
    t.fill(20, 4, 8, 20, 8, 12, AIR)
    t.fill(20, 3, 8, 20, 3, 12, st.path)
    t.jigsaw(20, 3, 10, "east_up", J_STREET, J_STREET, sp, st.path)

    # crossing rail lines
    ns_gaps = {4, 14} if st.decay else set()
    ew_gaps = {6, 16} if st.decay else set()
    for z in range(0, 21):
        if z not in ns_gaps:
            t.set(10, 4, z, "minecraft:rail", {"shape": "north_south"})
    for x in range(0, 21):
        if x != 10 and x not in ew_gaps:
            t.set(x, 4, 10, "minecraft:rail", {"shape": "east_west"})

    # mine shaft below plaza level, ringed by a fence
    t.fill(4, 1, 4, 5, 3, 5, AIR)
    t.set(4, 1, 4, "minecraft:rail", {"shape": "north_south"})
    t.entity(4, 1, 4, {"id": "minecraft:chest_minecart", "LootTable": MINESHAFT_LOOT})
    for x in range(3, 7):
        for z in range(3, 7):
            if x in (3, 6) or z in (3, 6):
                t.set(x, 4, z, st.fence)

    # headframe tower with a chain dropping into the shaft
    for x, z in ((3, 3), (6, 3), (3, 6), (6, 6)):
        t.fill(x, 4, z, x, 9, z, st.log, {"axis": "y"})
    t.fill(3, 10, 3, 6, 10, 6, st.plank)
    t.fill(4, 4, 4, 4, 9, 4, "minecraft:chain")
    if not st.decay:
        wall_torch(t, 3, 7, 4, "south")
        wall_torch(t, 6, 7, 5, "north")

    if st.light:
        lantern_post(t, st, 3, 4, 17)
        lantern_post(t, st, 17, 4, 3)
        lantern_post(t, st, 17, 4, 17)
        lantern_post(t, st, 15, 4, 7)

    if st.decay:
        t.set(1, 12, 1, "minecraft:cobweb")
        t.set(19, 12, 19, "minecraft:cobweb")
        t.set(3, 9, 4, "minecraft:cobweb")
        t.set(6, 9, 5, "minecraft:cobweb")
        t.fill(20, 4, 15, 20, 5, 16, AIR)  # breached east wall
        t.set(19, 4, 15, "minecraft:cobblestone")
        t.set(19, 4, 16, "minecraft:mossy_cobblestone")

    t.entity(10, 4, 15, {"id": "minecraft:minecart"})
    if st.decay:
        for x, y, z in ((14, 4, 6), (6, 4, 14), (12, 4, 12)):
            t.entity(x, y, z, zombie_villager_nbt(MINER))
    else:
        t.entity(14, 4, 6, villager_nbt("minecraft:plains", MINER))
        t.entity(6, 4, 14, villager_nbt("minecraft:plains", MINER))
    return t


# ---------------------------------------------------------------------------
# Mushroom village
# ---------------------------------------------------------------------------

def mushroom_center() -> T:
    st = MUSHROOM
    rnd = random.Random("mushroom:center")
    t = T(19, 13, 19)
    t.fill(0, 0, 0, 18, 12, 18, st.rock)
    t.fill(1, 1, 1, 17, 11, 17, AIR)
    t.fill(1, 0, 1, 17, 0, 17, "minecraft:mycelium")

    sp = streets_pool(st)
    t.fill(7, 1, 0, 11, 5, 0, AIR)
    t.fill(7, 0, 0, 11, 0, 0, st.path)
    t.jigsaw(9, 0, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.fill(7, 1, 18, 11, 5, 18, AIR)
    t.fill(7, 0, 18, 11, 0, 18, st.path)
    t.jigsaw(9, 0, 18, "south_up", J_STREET, J_STREET, sp, st.path)
    t.fill(0, 1, 7, 0, 5, 11, AIR)
    t.fill(0, 0, 7, 0, 0, 11, st.path)
    t.jigsaw(0, 0, 9, "west_up", J_STREET, J_STREET, sp, st.path)
    t.fill(18, 1, 7, 18, 5, 11, AIR)
    t.fill(18, 0, 7, 18, 0, 11, st.path)
    t.jigsaw(18, 0, 9, "east_up", J_STREET, J_STREET, sp, st.path)

    # giant mushroom in the plaza center
    t.fill(9, 1, 9, 9, 7, 9, STEM)
    t.fill(7, 8, 7, 11, 8, 11, "minecraft:red_mushroom_block")
    t.fill(8, 9, 8, 10, 9, 10, "minecraft:red_mushroom_block")
    for x, z in ((7, 7), (11, 7), (7, 11), (11, 11)):
        t.set(x, 8, z, SHROOMLIGHT)
    for x, z in ((4, 4), (14, 4), (4, 14), (14, 14)):
        t.set(x, 12, z, SHROOMLIGHT)

    # scattered small mushrooms
    spots = [(x, z) for x in range(2, 17) for z in range(2, 17)
             if not (6 <= x <= 12 and 6 <= z <= 12)]
    for x, z in rnd.sample(spots, 12):
        kind = "red_mushroom" if rnd.random() < 0.5 else "brown_mushroom"
        t.set(x, 1, z, f"minecraft:{kind}")

    for x, y, z in ((5, 1, 5), (13, 1, 6), (6, 1, 13)):
        t.entity(x, y, z, villager_nbt("undergroundvillages:mushroom", NONE))
    return t


def mushroom_house(red: bool) -> T:
    """A stem-walled hut with a giant-mushroom cap roof, standing in its own
    small carved cavern (gap on the sides/back/top so the cap is visible)."""
    st = MUSHROOM
    cap = "minecraft:red_mushroom_block" if red else "minecraft:brown_mushroom_block"
    sy = 11 if red else 10
    t = T(13, sy, 13)
    t.fill(0, 0, 0, 12, sy - 1, 12, st.rock)
    t.fill(1, 1, 1, 11, sy - 2, 11, AIR)
    t.fill(1, 0, 1, 11, 0, 11, "minecraft:mycelium")

    # hut footprint x=0..8, z=2..10; front wall flush with the template face
    t.fill(0, 1, 2, 0, 4, 10, STEM)
    t.fill(8, 1, 2, 8, 4, 10, STEM)
    t.fill(0, 1, 2, 8, 4, 2, STEM)
    t.fill(0, 1, 10, 8, 4, 10, STEM)
    if red:  # domed red cap
        t.fill(0, 5, 2, 8, 5, 10, cap)
        t.fill(1, 6, 3, 7, 6, 9, cap)
        t.fill(2, 7, 4, 6, 7, 8, cap)
        t.fill(3, 8, 5, 5, 8, 7, cap)
    else:  # wide flat brown cap with an overhang
        t.fill(0, 5, 1, 9, 5, 11, cap)
    t.set(3, 5, 6, SHROOMLIGHT)
    t.set(5, 5, 6, SHROOMLIGHT)

    door(t, 0, 1, 6, "west", st.door)
    t.jigsaw(0, 0, 6, "west_up", J_HOUSE, J_HOUSE, EMPTY, "minecraft:mycelium")

    # cavern dressing
    t.set(10, 1, 2, SHROOMLIGHT)
    t.set(10, 1, 10, SHROOMLIGHT)
    t.set(10, 1, 6, "minecraft:red_mushroom" if red else "minecraft:brown_mushroom")
    t.set(1, 1, 1, "minecraft:brown_mushroom")
    t.set(9, 1, 11, "minecraft:red_mushroom")

    if red:
        bed(t, 6, 1, 4, "east", "red")
        t.set(1, 1, 9, "minecraft:composter")
        t.set(1, 1, 3, "minecraft:barrel", {"facing": "up"},
              nbt={"id": "minecraft:barrel"})
        t.entity(3, 1, 5, villager_nbt("undergroundvillages:mushroom", NONE))
        t.entity(4, 1, 8, villager_nbt("undergroundvillages:mushroom", NONE))
    else:
        bed(t, 6, 1, 8, "east", "yellow")
        t.set(1, 1, 3, "minecraft:barrel", {"facing": "up"},
              nbt={"id": "minecraft:barrel"})
        t.entity(4, 1, 6, villager_nbt("undergroundvillages:mushroom", MINER))
        t.entity(10, 1, 4, villager_nbt("undergroundvillages:mushroom", NONE))
    return t


# ---------------------------------------------------------------------------
# Illager village
# ---------------------------------------------------------------------------

OMINOUS_BANNER_PATTERNS = [
    {"color": "cyan", "pattern": "minecraft:rhombus"},
    {"color": "light_gray", "pattern": "minecraft:stripe_bottom"},
    {"color": "gray", "pattern": "minecraft:stripe_center"},
    {"color": "light_gray", "pattern": "minecraft:border"},
    {"color": "black", "pattern": "minecraft:stripe_middle"},
    {"color": "light_gray", "pattern": "minecraft:half_horizontal"},
    {"color": "light_gray", "pattern": "minecraft:circle"},
    {"color": "black", "pattern": "minecraft:border"},
]


def illager_center() -> T:
    st = ILLAGER
    cd = "minecraft:cobbled_deepslate"
    t = T(19, 15, 19)
    t.fill(0, 0, 0, 18, 14, 18, st.rock)
    t.fill(1, 1, 1, 17, 13, 17, AIR)
    t.fill(1, 0, 1, 17, 0, 17, cd)

    sp = streets_pool(st)
    t.fill(7, 1, 0, 11, 5, 0, AIR)
    t.fill(7, 0, 0, 11, 0, 0, st.path)
    t.jigsaw(9, 0, 0, "north_up", J_STREET, J_STREET, sp, st.path)
    t.fill(7, 1, 18, 11, 5, 18, AIR)
    t.fill(7, 0, 18, 11, 0, 18, st.path)
    t.jigsaw(9, 0, 18, "south_up", J_STREET, J_STREET, sp, st.path)
    t.fill(0, 1, 7, 0, 5, 11, AIR)
    t.fill(0, 0, 7, 0, 0, 11, st.path)
    t.jigsaw(0, 0, 9, "west_up", J_STREET, J_STREET, sp, st.path)
    t.fill(18, 1, 7, 18, 5, 11, AIR)
    t.fill(18, 0, 7, 18, 0, 11, st.path)
    t.jigsaw(18, 0, 9, "east_up", J_STREET, J_STREET, sp, st.path)

    # central watchtower with the ominous banner on top
    t.fill(7, 1, 7, 11, 9, 7, cd)
    t.fill(7, 1, 11, 11, 9, 11, cd)
    t.fill(7, 1, 8, 7, 9, 10, cd)
    t.fill(11, 1, 8, 11, 9, 10, cd)
    t.fill(9, 1, 11, 9, 2, 11, AIR)  # tower doorway, south side
    for y in range(1, 10):
        t.set(9, y, 8, "minecraft:ladder", {"facing": "south"})
    t.fill(7, 10, 7, 11, 10, 11, st.plank)
    t.set(9, 10, 8, "minecraft:ladder", {"facing": "south"})
    for x, z in ((7, 7), (11, 7), (7, 11), (11, 11)):
        t.set(x, 11, z, cd)
    t.set(9, 11, 7, st.light, {"hanging": "false"})
    t.set(9, 11, 11, st.light, {"hanging": "false"})
    t.set(9, 11, 9, "minecraft:white_banner", {"rotation": "8"},
          nbt={"id": "minecraft:banner", "patterns": OMINOUS_BANNER_PATTERNS})

    for x, z in ((3, 3), (15, 3), (3, 15), (15, 15)):
        lantern_post(t, st, x, 1, z)

    t.entity(4, 1, 9, mob_nbt("minecraft:pillager"))
    t.entity(14, 1, 9, mob_nbt("minecraft:pillager"))
    return t


def illager_house() -> T:
    st = ILLAGER
    t = carved_room(st, 11, 8, 10, 4)
    corner_beams(t, st, 11, 8, 10)
    bed(t, 7, 1, 8, "east", "blue")
    t.set(1, 1, 7, "minecraft:crafting_table")
    t.set(1, 1, 6, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    hanging_light(t, st, 5, 6, 4)
    t.entity(4, 1, 3, mob_nbt("minecraft:vindicator"))
    t.entity(6, 1, 6, mob_nbt("minecraft:vindicator"))
    return t


def barracks() -> T:
    st = ILLAGER
    t = carved_room(st, 13, 8, 11, 5)
    corner_beams(t, st, 13, 8, 11)
    for i, x in enumerate((2, 4, 6)):
        bed(t, x, 1, 8, "south", "cyan")
    t.set(11, 1, 1, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(11, 2, 1, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(9, 1, 2, st.fence)
    t.set(9, 2, 2, "minecraft:oak_pressure_plate")
    hanging_light(t, st, 3, 6, 5)
    hanging_light(t, st, 9, 6, 5)
    t.entity(5, 1, 3, mob_nbt("minecraft:pillager"))
    t.entity(8, 1, 6, mob_nbt("minecraft:pillager"))
    return t


def basement_house(skulls: int) -> T:
    """The teaching house: ground floor plus a basement holding a wither-frame
    DISPLAY (igloo-lab style). NEVER 3 skulls -- that would summon a wither."""
    assert skulls in (1, 2)
    st = ILLAGER
    cd = "minecraft:cobbled_deepslate"
    t = T(11, 11, 10)
    t.fill(0, 0, 0, 10, 10, 9, st.rock)
    # basement
    t.fill(1, 1, 1, 9, 3, 8, AIR)
    t.fill(1, 0, 1, 9, 0, 8, cd)
    # ground floor slab + interior
    t.fill(1, 4, 1, 9, 4, 8, st.plank)
    t.fill(1, 5, 1, 9, 8, 8, AIR)
    # facade (only above street level; everything below stays buried)
    t.fill(0, 4, 0, 0, 10, 9, cd)
    door(t, 0, 5, 4, "west", st.door)
    t.jigsaw(0, 4, 4, "west_up", J_HOUSE, J_HOUSE, EMPTY, st.plank)

    # ladder well down to the basement
    for y in range(1, 6):
        t.set(9, y, 1, "minecraft:ladder", {"facing": "west"})

    # wither-summoning display frame against the basement's north wall:
    # soul sand T (1 base + 3 arms) with skulls ON TOP of the arms.
    t.set(4, 1, 1, "minecraft:soul_sand")
    t.fill(3, 2, 1, 5, 2, 1, "minecraft:soul_sand")
    t.set(4, 3, 1, "minecraft:wither_skeleton_skull", {"rotation": "8"},
          nbt={"id": "minecraft:skull"})
    if skulls == 2:
        t.set(3, 3, 1, "minecraft:wither_skeleton_skull", {"rotation": "8"},
              nbt={"id": "minecraft:skull"})

    loot_chest(t, 1, 1, 7, "east", "minecraft:chests/simple_dungeon")
    hanging_light(t, st, 5, 3, 4)
    hanging_light(t, st, 2, 3, 6)

    # ground floor furnishings
    bed(t, 5, 5, 8, "north", "blue")
    t.set(1, 5, 8, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(9, 5, 8, "minecraft:crafting_table")
    hanging_light(t, st, 5, 8, 4)
    t.entity(3, 5, 3, mob_nbt("minecraft:vindicator"))
    return t


# ---------------------------------------------------------------------------
# The tavern (single shared template, appears in mining/mushroom/illager)
# ---------------------------------------------------------------------------

def tavern() -> T:
    st = MINING
    planks = "minecraft:oak_planks"
    t = T(15, 12, 13)
    t.fill(0, 0, 0, 14, 11, 12, st.rock)
    # ground floor
    t.fill(1, 1, 1, 13, 5, 11, AIR)
    t.fill(1, 0, 1, 13, 0, 11, planks)
    # second storey
    t.fill(1, 6, 1, 13, 6, 11, planks)
    t.fill(1, 7, 1, 13, 10, 11, AIR)
    # facade + door
    t.fill(0, 0, 0, 0, 11, 12, st.face)
    door(t, 0, 1, 6, "west", st.door)
    t.jigsaw(0, 0, 6, "west_up", J_HOUSE, J_HOUSE, EMPTY, planks)

    # --- ground floor: the taproom -------------------------------------
    # bar counter with brewing stands on top
    t.fill(10, 1, 2, 10, 1, 7, planks)
    t.fill(10, 2, 2, 10, 2, 7, "minecraft:oak_slab", {"type": "bottom"})
    t.set(10, 2, 3, "minecraft:brewing_stand", nbt={"id": "minecraft:brewing_stand"})
    t.set(10, 2, 6, "minecraft:brewing_stand", nbt={"id": "minecraft:brewing_stand"})
    # brick fireplace set into the east wall, with the Tavern Hearth
    t.fill(13, 1, 4, 13, 2, 4, "minecraft:bricks")
    t.fill(13, 1, 6, 13, 2, 6, "minecraft:bricks")
    t.fill(13, 3, 4, 13, 3, 6, "minecraft:bricks")
    t.set(13, 1, 5, "undergroundvillages:tavern_hearth")
    # kitchen corner behind the bar
    t.set(13, 1, 2, "minecraft:smoker", {"facing": "west", "lit": "false"},
          nbt={"id": "minecraft:smoker"})
    t.set(13, 1, 8, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(13, 2, 8, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    t.set(12, 1, 8, "minecraft:barrel", {"facing": "up"}, nbt={"id": "minecraft:barrel"})
    # jukebox corner
    t.set(1, 1, 1, "minecraft:jukebox", nbt={"id": "minecraft:jukebox"})
    # tables: oak fence with a pressure-plate top
    for tx, tz in ((3, 3), (3, 9), (6, 8)):
        t.set(tx, 1, tz, st.fence)
        t.set(tx, 2, tz, "minecraft:oak_pressure_plate")
    # lighting
    for lx, lz in ((3, 5), (7, 2), (7, 9), (12, 5)):
        hanging_light(t, st, lx, 5, lz)

    # --- staircase up (along the south wall, z=10) ----------------------
    for i, x in enumerate(range(7, 13)):
        y = 1 + i
        if y > 1:
            t.fill(x, 1, 10, x, y - 1, 10, planks)
        if y < 6:
            t.set(x, y, 10, "minecraft:oak_stairs", {"facing": "east"})
    t.fill(9, 6, 10, 11, 6, 10, AIR)  # stairwell opening in the upper floor
    t.set(12, 6, 10, "minecraft:oak_stairs", {"facing": "east"})
    t.fill(9, 7, 9, 11, 7, 9, st.fence)  # stairwell railing

    # --- upstairs: four small bedrooms off two corridors ----------------
    # corridors: x=7 (z=1..8) and z=9..11 (main, with the stairwell)
    t.fill(6, 7, 1, 6, 9, 8, planks)
    t.fill(8, 7, 1, 8, 9, 8, planks)
    t.fill(1, 7, 4, 5, 9, 4, planks)
    t.fill(9, 7, 4, 13, 9, 4, planks)
    t.fill(1, 7, 8, 5, 9, 8, planks)
    t.fill(9, 7, 8, 13, 9, 8, planks)
    rooms = [
        (2, 2, "east", 6, 2, "east", "red"),      # NW: bed foot, door pos
        (2, 6, "east", 6, 6, "east", "green"),    # SW
        (11, 2, "west", 8, 2, "west", "blue"),    # NE
        (11, 6, "west", 8, 6, "west", "cyan"),    # SE
    ]
    for bx, bz, bface, dx, dz, dface, color in rooms:
        bed(t, bx, 7, bz, bface, color)
        door(t, dx, 7, dz, dface, st.door)
        hanging_light(t, st, bx + (2 if bface == "east" else -2), 10, bz)
    hanging_light(t, st, 7, 10, 5)
    hanging_light(t, st, 4, 10, 10)

    # --- patrons and staff ----------------------------------------------
    t.entity(12, 1, 5, villager_nbt("minecraft:plains",
                                    "undergroundvillages:tavern_keeper"))
    t.entity(4, 1, 4, villager_nbt("minecraft:plains", NONE))
    t.entity(5, 1, 8, villager_nbt("minecraft:plains", NONE))
    t.entity(2, 1, 9, {"id": "minecraft:witch", "PersistenceRequired": ("B", 1),
                       "Tags": ["uv_pacified"]})
    t.entity(7, 1, 7, {"id": "minecraft:wandering_trader",
                       "DespawnDelay": ("I", 0), "PersistenceRequired": ("B", 1)})
    t.entity(2, 1, 2, mob_nbt("undergroundvillages:mercenary"))
    t.entity(8, 1, 3, mob_nbt("undergroundvillages:collector"))
    return t


# ---------------------------------------------------------------------------
# Manifest + entry point
# ---------------------------------------------------------------------------

def build_all() -> dict[str, T]:
    out = {}
    for st in (MINING, ZOMBIE):
        out[f"{st.village}/town_center"] = mining_center(st)
        out[f"{st.village}/miner_house"] = miner_house(st)
        out[f"{st.village}/storage_house"] = storage_house(st)
        out[f"{st.village}/forge_house"] = forge_house(st)
    for st in (MINING, ZOMBIE, MUSHROOM, ILLAGER):
        out[f"{st.village}/street_straight"] = street_straight(st)
        out[f"{st.village}/street_corner"] = street_corner(st)
        out[f"{st.village}/street_t"] = street_t(st)
        out[f"{st.village}/terminator"] = terminator(st)
    out["mushroom_village/town_center"] = mushroom_center()
    out["mushroom_village/red_house"] = mushroom_house(red=True)
    out["mushroom_village/brown_house"] = mushroom_house(red=False)
    out["illager_village/town_center"] = illager_center()
    out["illager_village/illager_house"] = illager_house()
    out["illager_village/barracks"] = barracks()
    out["illager_village/basement_house"] = basement_house(1)
    out["illager_village/basement_house_lucky"] = basement_house(2)
    out["tavern"] = tavern()
    return out


def write_all(target: Path) -> dict[str, bytes]:
    data = {}
    for name, template in sorted(build_all().items()):
        blob = template.to_nbt()
        path = target / f"{name}.nbt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        data[name] = blob
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="regenerate into a temp dir and byte-compare "
                             "against the committed templates")
    args = parser.parse_args()

    if args.check:
        failures = []
        with tempfile.TemporaryDirectory(prefix="uv-structures-") as tmp:
            fresh = write_all(Path(tmp))
        for name, blob in sorted(fresh.items()):
            committed = OUT_DIR / f"{name}.nbt"
            if not committed.is_file():
                failures.append(f"missing: {committed}")
            elif committed.read_bytes() != blob:
                failures.append(f"stale: {committed}")
        committed_files = {p.relative_to(OUT_DIR).with_suffix("").as_posix()
                           for p in OUT_DIR.rglob("*.nbt")} if OUT_DIR.is_dir() else set()
        for extra in sorted(committed_files - set(fresh)):
            failures.append(f"unexpected template: {OUT_DIR / (extra + '.nbt')}")
        if failures:
            print("gen_structures --check FAILED:")
            for f in failures:
                print(f"  {f}")
            return 1
        print(f"gen_structures --check OK ({len(fresh)} templates match)")
        return 0

    data = write_all(OUT_DIR)
    for name, blob in sorted(data.items()):
        print(f"wrote {name}.nbt ({len(blob)} bytes)")
    print(f"{len(data)} templates -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
