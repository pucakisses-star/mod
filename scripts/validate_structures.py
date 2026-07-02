#!/usr/bin/env python3
"""Validate the Underground Villages structure templates and worldgen JSON.

Stdlib-only. Exits non-zero on any failure. Checks:
  (a) every template .nbt parses, DataVersion == 3955, each size axis <= 48,
      the box is fully populated, and every palette Name is in the vanilla
      block allowlist (plus our two custom blocks);
  (b) every template_pool element location resolves to an existing template
      .nbt (or is minecraft:empty) and its processors ref exists;
  (c) jigsaw wiring: every jigsaw's pool exists; for each jigsaw with pool P,
      at least one template referenced by P contains a jigsaw whose name
      equals this jigsaw's target; every horizontal jigsaw sits on the outer
      face it points at (vertical up_*/down_* jigsaws exempt);
  (d) every structure JSON's start_pool exists and its biomes tag resolves
      against the vanilla biome/tag lists;
  (e) structure_set files reference existing structures and use pairwise
      distinct salts;
  (f) template entity ids are within the allowed set.

The vanilla reference data directory ($VAN: block_ids.txt, biome_ids.txt,
data/minecraft/tags/worldgen/biome/) is located via --van or the VAN env var.
If it is missing, the checks that need it are skipped with a warning.
"""

import argparse
import gzip
import json
import os
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "src/main/resources"
UV = RES / "data/undergroundvillages"
STRUCTURE_DIR = UV / "structure"
POOL_DIR = UV / "worldgen/template_pool"
PROCESSOR_DIR = UV / "worldgen/processor_list"
STRUCTURE_JSON_DIR = UV / "worldgen/structure"
STRUCTURE_SET_DIR = UV / "worldgen/structure_set"
BIOME_TAG_DIR = UV / "tags/worldgen/biome"

DEFAULT_VAN = ("/tmp/claude-0/-home-user-mod/"
               "84c799a8-4b72-5c74-a265-190e1f940a93/scratchpad/vanilla")

DATA_VERSION = 3955
MAX_AXIS = 48
CUSTOM_BLOCKS = {"undergroundvillages:prospecting_table",
                 "undergroundvillages:tavern_hearth"}
ALLOWED_ENTITIES = {
    "minecraft:villager", "minecraft:zombie_villager", "minecraft:vindicator",
    "minecraft:pillager", "minecraft:witch", "minecraft:wandering_trader",
    "minecraft:chest_minecart", "minecraft:minecart",
    "undergroundvillages:mercenary", "undergroundvillages:collector",
}
EMPTY = "minecraft:empty"

# ---------------------------------------------------------------------------
# NBT reader (big-endian, gzipped)
# ---------------------------------------------------------------------------

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE, \
    TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, \
    TAG_LONG_ARRAY = range(13)


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        b = self.data[self.pos:self.pos + n]
        if len(b) != n:
            raise ValueError("truncated NBT")
        self.pos += n
        return b

    def unpack(self, fmt: str):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self) -> str:
        return self.take(self.unpack(">H")).decode("utf-8")


def _payload(r: _Reader, tag: int):
    if tag == TAG_BYTE:
        return r.unpack(">b")
    if tag == TAG_SHORT:
        return r.unpack(">h")
    if tag == TAG_INT:
        return r.unpack(">i")
    if tag == TAG_LONG:
        return r.unpack(">q")
    if tag == TAG_FLOAT:
        return r.unpack(">f")
    if tag == TAG_DOUBLE:
        return r.unpack(">d")
    if tag == TAG_BYTE_ARRAY:
        return list(r.take(r.unpack(">i")))
    if tag == TAG_STRING:
        return r.string()
    if tag == TAG_LIST:
        elem = r.unpack(">B")
        return [_payload(r, elem) for _ in range(r.unpack(">i"))]
    if tag == TAG_COMPOUND:
        out = {}
        while True:
            t = r.unpack(">B")
            if t == TAG_END:
                return out
            name = r.string()
            out[name] = _payload(r, t)
    if tag == TAG_INT_ARRAY:
        return [r.unpack(">i") for _ in range(r.unpack(">i"))]
    if tag == TAG_LONG_ARRAY:
        return [r.unpack(">q") for _ in range(r.unpack(">i"))]
    raise ValueError(f"unknown tag id {tag}")


def read_nbt(path: Path) -> dict:
    with gzip.open(path, "rb") as f:
        r = _Reader(f.read())
    if r.unpack(">B") != TAG_COMPOUND:
        raise ValueError("root is not a compound")
    r.string()  # root name
    return _payload(r, TAG_COMPOUND)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class Checker:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def template_path(location: str) -> Path | None:
    """Resolve an undergroundvillages: template location to its .nbt path."""
    ns, _, path = location.partition(":")
    if ns != "undergroundvillages":
        return None
    return STRUCTURE_DIR / f"{path}.nbt"


def pool_path(pool_id: str) -> Path | None:
    ns, _, path = pool_id.partition(":")
    if ns != "undergroundvillages":
        return None
    return POOL_DIR / f"{path}.json"


class Template:
    def __init__(self, path: Path, root: dict):
        self.path = path
        self.name = path.relative_to(STRUCTURE_DIR).with_suffix("").as_posix()
        self.size = root["size"]
        self.entities = root.get("entities", [])
        self.jigsaws = []  # (pos, orientation, nbt)
        palette = root["palette"]
        for block in root["blocks"]:
            state = palette[block["state"]]
            if state["Name"] == "minecraft:jigsaw":
                orientation = state.get("Properties", {}).get("orientation", "")
                self.jigsaws.append((block["pos"], orientation, block.get("nbt")))


def load_templates(ck: Checker, block_allowlist: set[str] | None) -> dict[str, Template]:
    templates: dict[str, Template] = {}
    paths = sorted(STRUCTURE_DIR.rglob("*.nbt")) if STRUCTURE_DIR.is_dir() else []
    if not paths:
        ck.error(f"no templates found under {STRUCTURE_DIR}")
        return templates
    for path in paths:
        rel = path.relative_to(STRUCTURE_DIR).as_posix()
        try:
            root = read_nbt(path)
        except Exception as exc:  # noqa: BLE001 - report and continue
            ck.error(f"{rel}: failed to parse: {exc}")
            continue
        if root.get("DataVersion") != DATA_VERSION:
            ck.error(f"{rel}: DataVersion {root.get('DataVersion')} != {DATA_VERSION}")
        size = root.get("size", [])
        if len(size) != 3 or any(not (0 < axis <= MAX_AXIS) for axis in size):
            ck.error(f"{rel}: bad size {size} (each axis must be 1..{MAX_AXIS})")
            continue
        volume = size[0] * size[1] * size[2]
        positions = {tuple(b["pos"]) for b in root["blocks"]}
        if len(root["blocks"]) != volume or len(positions) != volume:
            ck.error(f"{rel}: box not fully populated "
                     f"({len(root['blocks'])} blocks, volume {volume})")
        for state in root["palette"]:
            name = state["Name"]
            if name in CUSTOM_BLOCKS:
                continue
            if block_allowlist is not None:
                if name.removeprefix("minecraft:") not in block_allowlist:
                    ck.error(f"{rel}: palette block not in allowlist: {name}")
        tpl = Template(path, root)
        templates[tpl.name] = tpl
    return templates


def load_pools(ck: Checker, templates: dict[str, Template]) -> dict[str, list[str]]:
    """Return pool id -> list of member template names. Validates (b)."""
    pools: dict[str, list[str]] = {}
    paths = sorted(POOL_DIR.rglob("*.json")) if POOL_DIR.is_dir() else []
    if not paths:
        ck.error(f"no template pools found under {POOL_DIR}")
    for path in paths:
        rel = path.relative_to(POOL_DIR).with_suffix("").as_posix()
        pool_id = f"undergroundvillages:{rel}"
        data = json.loads(path.read_text())
        members: list[str] = []
        fallback = data.get("fallback")
        if fallback != EMPTY and (pool_path(fallback) is None
                                  or not pool_path(fallback).is_file()):
            ck.error(f"pool {pool_id}: fallback pool does not exist: {fallback}")
        for entry in data.get("elements", []):
            elem = entry.get("element", {})
            etype = elem.get("element_type")
            if etype == "minecraft:empty_pool_element":
                continue
            location = elem.get("location", "")
            if location == EMPTY:
                continue
            tpath = template_path(location)
            if tpath is None or not tpath.is_file():
                ck.error(f"pool {pool_id}: element location does not resolve "
                         f"to a template: {location}")
            else:
                members.append(tpath.relative_to(STRUCTURE_DIR)
                               .with_suffix("").as_posix())
            processors = elem.get("processors", EMPTY)
            if processors != EMPTY:
                ns, _, ppath = processors.partition(":")
                if ns != "undergroundvillages" or \
                        not (PROCESSOR_DIR / f"{ppath}.json").is_file():
                    ck.error(f"pool {pool_id}: processors ref does not exist: "
                             f"{processors}")
        pools[pool_id] = members
    return pools


FACE_AXES = {"west": (0, 0), "east": (0, 1), "north": (2, 0), "south": (2, 1)}


def check_jigsaws(ck: Checker, templates: dict[str, Template],
                  pools: dict[str, list[str]]) -> None:
    for tpl in templates.values():
        for pos, orientation, nbt in tpl.jigsaws:
            where = f"{tpl.name} jigsaw@{pos}"
            if not nbt or nbt.get("id") != "minecraft:jigsaw":
                ck.error(f"{where}: jigsaw block without jigsaw block entity")
                continue
            pool = nbt.get("pool", "")
            target = nbt.get("target", "")
            # pool must exist
            if pool != EMPTY:
                ppath = pool_path(pool)
                if ppath is None or not ppath.is_file():
                    ck.error(f"{where}: pool does not exist: {pool}")
                elif pool not in pools:
                    ck.error(f"{where}: pool not loaded: {pool}")
                else:
                    # some template in the pool must answer to our target
                    names = set()
                    for member in pools[pool]:
                        mem = templates.get(member)
                        if mem:
                            names.update(j[2].get("name") for j in mem.jigsaws
                                         if j[2])
                    if target not in names:
                        ck.error(f"{where}: no template in {pool} has a jigsaw "
                                 f"named {target}")
            # face rule: horizontal jigsaws must sit on the face they point at
            front = orientation.split("_", 1)[0] if orientation else ""
            if front in ("up", "down"):
                continue
            if front not in FACE_AXES:
                ck.error(f"{where}: bad orientation {orientation!r}")
                continue
            axis, side = FACE_AXES[front]
            expected = 0 if side == 0 else tpl.size[axis] - 1
            if pos[axis] != expected:
                ck.error(f"{where}: points {front} but sits at "
                         f"{'xyz'[axis]}={pos[axis]} (expected {expected}, "
                         f"size {tpl.size})")


def check_biome_value(ck: Checker, value: str, van: Path | None,
                      biome_ids: set[str] | None, context: str,
                      seen: set[str]) -> None:
    if value.startswith("#"):
        ns, _, path = value[1:].partition(":")
        if ns == "minecraft":
            if van is None:
                return
            if not (van / "data/minecraft/tags/worldgen/biome" / f"{path}.json").is_file():
                ck.error(f"{context}: vanilla biome tag does not exist: {value}")
        elif ns == "undergroundvillages":
            check_biome_tag_file(ck, BIOME_TAG_DIR / f"{path}.json", van,
                                 biome_ids, seen)
        else:
            ck.error(f"{context}: unknown tag namespace: {value}")
        return
    ns, _, path = value.partition(":")
    if ns != "minecraft":
        ck.error(f"{context}: unknown biome namespace: {value}")
        return
    if biome_ids is not None and path not in biome_ids:
        ck.error(f"{context}: biome not in vanilla biome list: {value}")


def check_biome_tag_file(ck: Checker, path: Path, van: Path | None,
                         biome_ids: set[str] | None, seen: set[str]) -> None:
    key = str(path)
    if key in seen:
        return
    seen.add(key)
    if not path.is_file():
        ck.error(f"biome tag file does not exist: {path}")
        return
    data = json.loads(path.read_text())
    for value in data.get("values", []):
        if isinstance(value, dict):
            value = value.get("id", "")
        check_biome_value(ck, value, van, biome_ids,
                          path.relative_to(RES).as_posix(), seen)


def check_structures(ck: Checker, van: Path | None,
                     biome_ids: set[str] | None) -> set[str]:
    names: set[str] = set()
    paths = sorted(STRUCTURE_JSON_DIR.glob("*.json")) \
        if STRUCTURE_JSON_DIR.is_dir() else []
    if not paths:
        ck.error(f"no structure JSON found under {STRUCTURE_JSON_DIR}")
    seen: set[str] = set()
    for path in paths:
        name = path.stem
        names.add(f"undergroundvillages:{name}")
        data = json.loads(path.read_text())
        start_pool = data.get("start_pool", "")
        ppath = pool_path(start_pool)
        if ppath is None or not ppath.is_file():
            ck.error(f"structure {name}: start_pool does not exist: {start_pool}")
        biomes = data.get("biomes")
        values = biomes if isinstance(biomes, list) else [biomes]
        for value in values:
            check_biome_value(ck, value, van, biome_ids,
                              f"structure {name} biomes", seen)
    # also validate every one of our biome tag files, referenced or not
    if BIOME_TAG_DIR.is_dir():
        for path in sorted(BIOME_TAG_DIR.rglob("*.json")):
            check_biome_tag_file(ck, path, van, biome_ids, seen)
    return names


def check_structure_sets(ck: Checker, structures: set[str]) -> None:
    paths = sorted(STRUCTURE_SET_DIR.glob("*.json")) \
        if STRUCTURE_SET_DIR.is_dir() else []
    if not paths:
        ck.error(f"no structure sets found under {STRUCTURE_SET_DIR}")
    salts: dict[int, str] = {}
    for path in paths:
        data = json.loads(path.read_text())
        for entry in data.get("structures", []):
            ref = entry.get("structure", "")
            if ref not in structures:
                ck.error(f"structure_set {path.stem}: unknown structure {ref}")
        salt = data.get("placement", {}).get("salt")
        if salt is None:
            ck.error(f"structure_set {path.stem}: missing placement salt")
        elif salt in salts:
            ck.error(f"structure_set {path.stem}: salt {salt} duplicates "
                     f"{salts[salt]}")
        else:
            salts[salt] = path.stem


def check_entities(ck: Checker, templates: dict[str, Template]) -> None:
    for tpl in templates.values():
        for entity in tpl.entities:
            eid = entity.get("nbt", {}).get("id")
            if eid not in ALLOWED_ENTITIES:
                ck.error(f"{tpl.name}: entity id not allowed: {eid}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--van", default=os.environ.get("VAN", DEFAULT_VAN),
                        help="vanilla reference data dir (block_ids.txt, "
                             "biome_ids.txt, data/minecraft/tags/...)")
    args = parser.parse_args()

    ck = Checker()
    van = Path(args.van)
    block_allowlist = biome_ids = None
    if van.is_dir():
        block_allowlist = set((van / "block_ids.txt").read_text().split())
        biome_ids = set((van / "biome_ids.txt").read_text().split())
    else:
        van = None
        ck.warn("vanilla reference data not found; skipped block/biome "
                "allowlist checks (pass --van or set VAN)")

    templates = load_templates(ck, block_allowlist)
    pools = load_pools(ck, templates)
    check_jigsaws(ck, templates, pools)
    structures = check_structures(ck, van, biome_ids)
    check_structure_sets(ck, structures)
    check_entities(ck, templates)

    # summary table
    rows = [(t.name, "x".join(map(str, t.size)), len(t.jigsaws), len(t.entities))
            for t in sorted(templates.values(), key=lambda t: t.name)]
    width = max((len(r[0]) for r in rows), default=8)
    print(f"{'template'.ljust(width)}  {'size':>10}  {'jigsaws':>7}  {'entities':>8}")
    print(f"{'-' * width}  {'-' * 10}  {'-' * 7}  {'-' * 8}")
    for name, size, njig, nent in rows:
        print(f"{name.ljust(width)}  {size:>10}  {njig:>7}  {nent:>8}")
    print(f"{len(rows)} templates, {len(pools)} pools, "
          f"{len(structures)} structures")

    for warning in ck.warnings:
        print(f"WARNING: {warning}")
    if ck.errors:
        print(f"\nFAILED with {len(ck.errors)} error(s):")
        for err in ck.errors:
            print(f"  {err}")
        return 1
    print("\nAll validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
