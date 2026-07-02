package com.undergroundvillages.registry;

import com.google.common.collect.ImmutableSet;
import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.mixin.VillagerTypeAccessor;

import net.fabricmc.fabric.api.object.builder.v1.trade.TradeOfferHelper;
import net.fabricmc.fabric.api.object.builder.v1.world.poi.PointOfInterestHelper;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.ai.village.poi.PoiType;
import net.minecraft.world.entity.npc.VillagerProfession;
import net.minecraft.world.entity.npc.VillagerTrades;
import net.minecraft.world.entity.npc.VillagerType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.biome.Biomes;

/**
 * Villager content: points of interest, the Miner and Tavern Keeper
 * professions with their trade tables, and the Mushroom villager type.
 */
public final class UVVillagers {
    private static final float PRICE_MULTIPLIER = 0.05f;

    public static final ResourceKey<PoiType> MINER_POI_KEY =
            ResourceKey.create(Registries.POINT_OF_INTEREST_TYPE, UndergroundVillages.id("miner"));
    public static final ResourceKey<PoiType> TAVERN_KEEPER_POI_KEY =
            ResourceKey.create(Registries.POINT_OF_INTEREST_TYPE, UndergroundVillages.id("tavern_keeper"));

    public static final PoiType MINER_POI = PointOfInterestHelper.register(
            UndergroundVillages.id("miner"), 1, 1, UVBlocks.PROSPECTING_TABLE);
    public static final PoiType TAVERN_KEEPER_POI = PointOfInterestHelper.register(
            UndergroundVillages.id("tavern_keeper"), 1, 1, UVBlocks.TAVERN_HEARTH);

    public static final VillagerProfession MINER = Registry.register(
            BuiltInRegistries.VILLAGER_PROFESSION,
            UndergroundVillages.id("miner"),
            new VillagerProfession(
                    "undergroundvillages:miner",
                    holder -> holder.is(MINER_POI_KEY),
                    holder -> holder.is(MINER_POI_KEY),
                    ImmutableSet.of(),
                    ImmutableSet.of(),
                    SoundEvents.VILLAGER_WORK_TOOLSMITH));

    public static final VillagerProfession TAVERN_KEEPER = Registry.register(
            BuiltInRegistries.VILLAGER_PROFESSION,
            UndergroundVillages.id("tavern_keeper"),
            new VillagerProfession(
                    "undergroundvillages:tavern_keeper",
                    holder -> holder.is(TAVERN_KEEPER_POI_KEY),
                    holder -> holder.is(TAVERN_KEEPER_POI_KEY),
                    ImmutableSet.of(),
                    ImmutableSet.of(),
                    SoundEvents.VILLAGER_WORK_BUTCHER));

    public static final VillagerType MUSHROOM = Registry.register(
            BuiltInRegistries.VILLAGER_TYPE,
            UndergroundVillages.id("mushroom"),
            new VillagerType("mushroom"));

    private UVVillagers() {
    }

    public static void init() {
        VillagerTypeAccessor.getByBiome().put(Biomes.LUSH_CAVES, MUSHROOM);
        VillagerTypeAccessor.getByBiome().put(Biomes.MUSHROOM_FIELDS, MUSHROOM);

        registerMinerTrades();
        registerTavernKeeperTrades();
    }

    private static void registerMinerTrades() {
        // Level 1 (xp 2): coal for emeralds, emeralds for raw copper.
        TradeOfferHelper.registerVillagerOffers(MINER, 1, factories -> {
            factories.add(offer(Items.COAL, 15, Items.EMERALD, 1, 16, 2));
            factories.add(offer(Items.EMERALD, 1, Items.RAW_COPPER, 12, 16, 2));
        });

        // Level 2 (xp 5): ore-for-ore, raw iron for emeralds, torches.
        TradeOfferHelper.registerVillagerOffers(MINER, 2, factories -> {
            factories.add(offer(Items.RAW_COPPER, 9, Items.RAW_IRON, 4, 12, 5));
            factories.add(offer(Items.RAW_IRON, 16, Items.EMERALD, 3, 12, 5));
            factories.add(offer(Items.EMERALD, 1, Items.TORCH, 16, 16, 5));
        });

        // Level 3 (xp 10): raw gold, the Mining Hat, rails, minecarts.
        TradeOfferHelper.registerVillagerOffers(MINER, 3, factories -> {
            factories.add(offer(Items.RAW_IRON, 4, Items.RAW_GOLD, 1, 12, 10));
            factories.add(offer(Items.EMERALD, 24, UVItems.MINING_HAT, 1, 3, 10));
            factories.add(offer(Items.EMERALD, 3, Items.RAIL, 16, 12, 10));
            factories.add(offer(Items.EMERALD, 6, Items.MINECART, 1, 12, 10));
        });

        // Level 4 (xp 15): lapis and redstone buying, gold back to iron.
        TradeOfferHelper.registerVillagerOffers(MINER, 4, factories -> {
            factories.add(offer(Items.LAPIS_LAZULI, 8, Items.EMERALD, 1, 12, 15));
            factories.add(offer(Items.REDSTONE, 16, Items.EMERALD, 1, 12, 15));
            factories.add(offer(Items.RAW_GOLD, 2, Items.RAW_IRON, 5, 12, 15));
        });

        // Level 5 (xp 30): diamonds and amethyst.
        TradeOfferHelper.registerVillagerOffers(MINER, 5, factories -> {
            factories.add(offer(Items.EMERALD, 12, Items.DIAMOND, 2, 3, 30));
            factories.add(offer(Items.EMERALD, 1, Items.AMETHYST_SHARD, 4, 12, 30));
        });
    }

    private static void registerTavernKeeperTrades() {
        // Level 1 (xp 2): food and brews.
        TradeOfferHelper.registerVillagerOffers(TAVERN_KEEPER, 1, factories -> {
            factories.add(offer(Items.EMERALD, 1, Items.SUSPICIOUS_STEW, 1, 12, 2));
            factories.add(offer(Items.EMERALD, 1, Items.MUSHROOM_STEW, 1, 12, 2));
            factories.add(offer(Items.EMERALD, 1, Items.HONEY_BOTTLE, 1, 12, 2));
            factories.add(offer(Items.SWEET_BERRIES, 10, Items.EMERALD, 1, 12, 2));
        });

        // Level 2 (xp 5): music discs for the jukebox.
        TradeOfferHelper.registerVillagerOffers(TAVERN_KEEPER, 2, factories -> {
            factories.add(offer(Items.EMERALD, 8, Items.MUSIC_DISC_CAT, 1, 2, 5));
            factories.add(offer(Items.EMERALD, 8, Items.MUSIC_DISC_BLOCKS, 1, 2, 5));
        });

        // Level 3 (xp 10): Parrot Cracker.
        TradeOfferHelper.registerVillagerOffers(TAVERN_KEEPER, 3, factories ->
                factories.add(offer(Items.EMERALD, 8, UVItems.PARROT_CRACKER, 1, 3, 10)));

        // Level 4 (xp 15): Cat Bell.
        TradeOfferHelper.registerVillagerOffers(TAVERN_KEEPER, 4, factories ->
                factories.add(offer(Items.EMERALD, 10, UVItems.CAT_BELL, 1, 3, 15)));

        // Level 5 (xp 30): Wolf Whistle.
        TradeOfferHelper.registerVillagerOffers(TAVERN_KEEPER, 5, factories ->
                factories.add(offer(Items.EMERALD, 12, UVItems.WOLF_WHISTLE, 1, 3, 30)));
    }

    /**
     * Creates a single-cost trade listing. The {@link MerchantOffer} (and its
     * result stack) is built fresh for every villager that rolls the trade.
     */
    private static VillagerTrades.ItemListing offer(ItemLike costItem, int costCount,
            ItemLike resultItem, int resultCount, int maxUses, int xp) {
        return (trader, random) -> new MerchantOffer(
                new ItemCost(costItem, costCount),
                new ItemStack(resultItem, resultCount),
                maxUses, xp, PRICE_MULTIPLIER);
    }
}
