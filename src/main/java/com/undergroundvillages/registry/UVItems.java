package com.undergroundvillages.registry;

import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.item.MiningHatItem;
import com.undergroundvillages.item.PetSummonItem;
import net.fabricmc.fabric.api.itemgroup.v1.FabricItemGroup;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.SpawnEggItem;

/**
 * Items, spawn eggs and the creative tab for Underground Villages.
 */
public final class UVItems {
    public static final Item MINING_HAT = register("mining_hat", new MiningHatItem());

    public static final Item WOLF_WHISTLE = register("wolf_whistle",
        new PetSummonItem(PetSummonItem.Kind.WOLF, new Item.Properties().stacksTo(16)));
    public static final Item CAT_BELL = register("cat_bell",
        new PetSummonItem(PetSummonItem.Kind.CAT, new Item.Properties().stacksTo(16)));
    public static final Item PARROT_CRACKER = register("parrot_cracker",
        new PetSummonItem(PetSummonItem.Kind.PARROT, new Item.Properties().stacksTo(16)));

    public static final Item MERCENARY_SPAWN_EGG = register("mercenary_spawn_egg",
        new SpawnEggItem(UVEntities.MERCENARY, 0x5b7c3a, 0xb02e26, new Item.Properties()));
    public static final Item COLLECTOR_SPAWN_EGG = register("collector_spawn_egg",
        new SpawnEggItem(UVEntities.COLLECTOR, 0x2f2f3a, 0xc9a34e, new Item.Properties()));

    public static final CreativeModeTab MAIN_TAB = Registry.register(
        BuiltInRegistries.CREATIVE_MODE_TAB,
        UndergroundVillages.id("main"),
        FabricItemGroup.builder()
            .title(Component.translatable("itemGroup.undergroundvillages.main"))
            .icon(() -> new ItemStack(MINING_HAT))
            .displayItems((params, output) -> {
                output.accept(UVBlocks.PROSPECTING_TABLE);
                output.accept(UVBlocks.TAVERN_HEARTH);
                output.accept(MINING_HAT);
                output.accept(WOLF_WHISTLE);
                output.accept(CAT_BELL);
                output.accept(PARROT_CRACKER);
                output.accept(MERCENARY_SPAWN_EGG);
                output.accept(COLLECTOR_SPAWN_EGG);
            })
            .build());

    private UVItems() {
    }

    private static Item register(String name, Item item) {
        return Registry.register(BuiltInRegistries.ITEM, UndergroundVillages.id(name), item);
    }

    public static void init() {
        // Triggers static registration.
    }
}
