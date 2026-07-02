# Underground Villages — Design & Implementation Spec

Target: **Minecraft 1.21.1, Fabric Loader 0.19.3, Fabric API 0.116.13+1.21.1, Mojang official mappings (Mojmap), Java 21.**

Mod ID: `undergroundvillages` — base package `com.undergroundvillages`.
Helper: `UndergroundVillages.id(String path)` returns `ResourceLocation.fromNamespaceAndPath(MOD_ID, path)`.

## Features (player-facing)

1. **Underground villages** generate inside caves, fully carved into stone, in four variants:
   - **Mining village** (most overworld biomes, deep underground): rail lines zigzag between houses,
     minecarts, lantern posts, ore-flecked walls, miner villagers.
   - **Mushroom village** (lush caves + mushroom fields): houses built from giant-mushroom blocks,
     mycelium paths, shroomlights, villagers with mushrooms growing on them (custom villager type).
   - **Zombie village** (dripstone caves + rare elsewhere): decayed, dark, cobwebbed variant of the
     mining village inhabited only by zombie villagers.
   - **Illager village** (deep dark): cobbled-deepslate/dark-oak houses lit by soul lanterns,
     inhabited by hostile vindicators and pillagers. One house has a basement containing a
     wither-summoning frame (soul sand T) with 1 guaranteed + 1 lucky (50%) wither skeleton skull —
     an igloo-style "teaching" structure.
2. **Miner villagers**: custom profession, workstation = Prospecting Table. Trades are ore-for-ore
   both directions plus ores-for-emeralds (explains where emeralds come from), sells the Mining Hat,
   rails, minecarts, torches.
3. **Mining Hat**: helmet item. While worn, it emits light — the mod places/removes invisible
   `minecraft:light` blocks at the player's head as they move.
4. **Taverns**: a two-story building that can appear in any village variant. Ground floor: bar,
   jukebox, brewing stands, tables. Upstairs: several small bedrooms. Inhabitants: a Tavern Keeper
   villager (unique trades: tamed pets via Wolf Whistle / Cat Bell / Parrot Cracker, music discs,
   food), regular villagers, a pacified witch, a wandering trader, a Mercenary, and the Collector.
5. **Tavern pacification**: the Tavern Hearth block pacifies any hostile mob within its radius
   (tagged `uv_pacified`, persistent). Pacified mobs never target players again — bring a creeper or
   witch into a tavern and it becomes a peaceful patron.
6. **Pacified witches trade potions** on right-click (healing, swiftness, fire res, night vision, …).
7. **Mercenary**: pay 30 emeralds → follows the hirer and attacks hostile mobs like an iron golem
   for 3 in-game days, then walks/teleports back home to the tavern and can be re-hired.
8. **The Collector**: a non-hostile illager in taverns who pays a fortune in emeralds for Nether
   Stars (48) and Dragon Heads (64) — but every deal empowers the illagers: the next raid's raiders
   gain buffs and enchanted weapons (one raid empowered per deal, tracked per level in SavedData).

## Registry IDs (namespace `undergroundvillages`)

| Kind | ID |
|---|---|
| Block | `prospecting_table`, `tavern_hearth` |
| Item | `prospecting_table`, `tavern_hearth` (block items), `mining_hat`, `wolf_whistle`, `cat_bell`, `parrot_cracker`, `mercenary_spawn_egg`, `collector_spawn_egg` |
| Armor material | `mining_hat` |
| Entity | `mercenary`, `collector` |
| Block entity | `tavern_hearth` |
| POI | `miner`, `tavern_keeper` |
| Profession | `miner`, `tavern_keeper` |
| Villager type | `mushroom` |
| Creative tab | `main` |
| Structures | `mining_village`, `mushroom_village`, `zombie_village`, `illager_village` |

## Java layout (`com.undergroundvillages`)

- `UndergroundVillages` — ModInitializer; calls `UVBlocks.init()`, `UVItems.init()`,
  `UVBlockEntities.init()`, `UVEntities.init()`, `UVVillagers.init()`, `TavernPacification.init()`,
  `WitchTrading.init()`, `MiningHatLight.init()`.
- `registry/UVBlocks` — blocks + block items. Plain `Block` registration (1.21.1 style, no id in
  Properties).
- `registry/UVItems` — items, armor material, spawn eggs, creative tab.
- `registry/UVBlockEntities` — `TAVERN_HEARTH` BlockEntityType.
- `registry/UVEntities` — entity types + `FabricDefaultAttributeRegistry`.
- `registry/UVVillagers` — POIs (`PointOfInterestHelper.register`), professions, trades
  (`TradeOfferHelper.registerVillagerOffers`), mushroom `VillagerType` + biome map injection via
  `VillagerTypeAccessor`.
- `block/ProspectingTableBlock`, `block/TavernHearthBlock`, `block/TavernHearthBlockEntity`.
- `item/MiningHatItem` (ArmorItem, HELMET), `item/PetSummonItem` (spawns pre-tamed pet, consumes).
- `light/MiningHatLight` — server tick handler managing `minecraft:light` blocks (place at head pos,
  clean up on move/unequip/disconnect/dimension change; waterlog-aware).
- `entity/MercenaryEntity`, `entity/CollectorEntity`.
- `tavern/Pacification` — `TAG = "uv_pacified"`, `isPacified(Entity)`, `pacify(Mob)`;
  `tavern/TavernPacification` — hearth scan logic helpers.
- `trading/AdhocMerchant` — `Merchant` impl wrapping any LivingEntity + `MerchantOffers`; used for
  witches and the Collector; `openTradingScreen` via the Merchant default method.
- `trading/WitchTrading` — `UseEntityCallback` for pacified witches; deterministic per-witch potion
  offers (seed from witch UUID).
- `trading/CollectorTrades` — offer factory + trade callback incrementing raid empowerment.
- `raid/RaidEmpowermentData` — `SavedData` per ServerLevel: `pendingEmpowerments` int +
  `empoweredRaidIds` set; `empower()`, `tryConsumeForRaid(int raidId)`, `isRaidEmpowered(int)`.
- `mixin/MobSetTargetMixin` — cancels `Mob.setTarget(player)` for pacified mobs.
- `mixin/RaidJoinMixin` — `Raid#joinRaid` TAIL: consume empowerment, buff raider + enchanted gear.
- `mixin/VillagerTypeAccessor` — accessor for `VillagerType.BY_BIOME` map.
- `client/UndergroundVillagesClient` + `client/render/MercenaryRenderer`, `client/render/CollectorRenderer`
  — both use `VillagerModel` (`ModelLayers.VILLAGER`) with mod textures
  `textures/entity/mercenary.png`, `textures/entity/collector.png`.

## 1.21.1 data-format rules (IMPORTANT — do not use pre-1.21 names)

- Structure NBT templates: `data/undergroundvillages/structure/<name>.nbt` (folder singular).
  `DataVersion` = **3955**.
- Loot tables: `data/<ns>/loot_table/...` (singular).
- Worldgen JSON: `data/undergroundvillages/worldgen/structure/`, `worldgen/structure_set/`,
  `worldgen/template_pool/`, `worldgen/processor_list/`.
- Biome tags: `data/undergroundvillages/tags/worldgen/biome/has_structure/<name>.json`.
- POI tag (required so villagers can take our jobs):
  `data/minecraft/tags/point_of_interest_type/acquirable_job_site.json` with `"replace": false`,
  values `["undergroundvillages:miner", "undergroundvillages:tavern_keeper"]`.
- Jigsaw structure JSON fields: `type: "minecraft:jigsaw"`, `biomes` (tag ref), `step:
  "underground_structures"`, `spawn_overrides: {}`, `terrain_adaptation: "none"`, `start_pool`,
  `size` (jigsaw depth), `start_height` (uniform absolute -36..-12), `use_expansion_hack: false`,
  `max_distance_from_center: 80`. No `project_start_to_heightmap` (we want fully underground).
- Structure sets: `placement.type: "minecraft:random_spread"`, distinct `salt` per set.
- Structure templates carve their own caverns: every template is a full box that includes air.

## Jigsaw conventions

Pools live under `undergroundvillages:<village>/<pool>`: `town_center`, `streets`, `houses`,
`terminators`. Connector contract (same names across all villages):

- Street connectors: jigsaw `name` = `undergroundvillages:street`, `target` =
  `undergroundvillages:street`, pool = `<village>/streets`, joint `rollable` for center pieces.
- House sockets on streets: `target` = `undergroundvillages:house`, pool = `<village>/houses`;
  every house has one jigsaw block at its door with `name` = `undergroundvillages:house` facing out.
- Streets' fallback pool = `<village>/terminators` (solid wall plug pieces) so open tunnel ends get
  capped.
- The tavern is a rare heavy piece in each village's `houses` pool (single shared/per-variant
  template `tavern`).

## Entities inside templates

Spawned via template entity NBT, all with `PersistenceRequired: 1b`:
- Villagers: `VillagerData {type, profession, level: 2}`, `Xp: 10` (level 2 prevents reroll).
  Mining village: profession `undergroundvillages:miner`; type `minecraft:plains`.
  Mushroom village: type `undergroundvillages:mushroom`.
- Zombie villages: `minecraft:zombie_villager` with matching VillagerData.
- Illager village: `minecraft:vindicator` / `minecraft:pillager` (hostile, `CanJoinRaid: 1b`... omit;
  plain).
- Tavern: tavern keeper villager, plains villagers, `minecraft:witch` with `Tags: ["uv_pacified"]`,
  `minecraft:wandering_trader` with `DespawnDelay: 0`, `undergroundvillages:mercenary`,
  `undergroundvillages:collector`.

## Behavior details

- **Pacification**: Hearth BE ticks every 40 game ticks, radius 16 (y ±8). Targets `Mob` instances
  that are `Enemy` (or `Witch`): add `uv_pacified` command tag, `setTarget(null)`,
  `setPersistenceRequired()`, stop NeutralMob anger. The `MobSetTargetMixin` makes the tag permanent
  even outside the tavern.
- **Mercenary**: 40 HP, 6 attack, speed 0.33. States: IDLE (wander near home) → HIRED (right-click
  with ≥30 emeralds; consumes 30) → follows employer (teleports if >32 blocks), attacks Monsters
  within 16 blocks of employer (never pacified ones), expires after 72000 ticks → RETURNING (paths
  home, teleports if >128 or arrives) → IDLE. Persists employer UUID, expiry game time, home pos.
- **Collector trades**: 1 nether star → 48 emeralds; 1 dragon head → 64 emeralds. Each completed
  trade: `RaidEmpowermentData.empower()` on that level + ominous chat line to the trader.
- **Raid empowerment**: on `Raid#joinRaid`, first raider of a raid consumes one pending empowerment
  and marks the raid id; every raider joining a marked raid gets: +10 max health (healed), Speed I +
  Resistance I (infinite), Vindicators: diamond axe + Sharpness III, Pillagers: crossbow + Quick
  Charge II & Piercing II (enchant via `Registries.ENCHANTMENT` holders).
- **Witch offers** (deterministic per witch UUID, maxUses 12): 4 random sell-potion offers from
  {healing, strong healing, swiftness, fire resistance, night vision, water breathing, regeneration,
  strength} at 5–9 emeralds, plus buys glass bottles (8→1 em) and nether wart (6→1 em).
- **Miner trades**: L1: 15 coal→1em, 1em→12 raw copper; L2: 9 raw copper→4 raw iron (ore-for-ore),
  16 raw iron→3em, 1em→2 torches ×16; L3: 4 raw iron→1 raw gold, 24em→Mining Hat, 3em→16 rails +
  minecart trades; L4: 8 lapis/16 redstone→em, 2 raw gold→5 raw iron; L5: 12em→2 diamonds,
  1em→amethyst shards.
- **Tavern keeper trades**: L1: food/brews (suspicious stew, honey bottle, mushroom stew); L2: 8em→
  music disc (cat/blocks); L3: 8em→Parrot Cracker; L4: 10em→Cat Bell; L5: 12em→Wolf Whistle.
- **Pet items**: use on ground (server side): spawns Wolf/Cat/Parrot already tamed by the user
  (random cat/parrot variant), consumes the item, plays a sound.
