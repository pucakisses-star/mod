package com.undergroundvillages.registry;

import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.block.TavernHearthBlock;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;

/**
 * Blocks and their block items for Underground Villages.
 */
public final class UVBlocks {
    public static final Block PROSPECTING_TABLE = register("prospecting_table", new Block(
        BlockBehaviour.Properties.of()
            .mapColor(MapColor.STONE)
            .strength(2.5f)
            .sound(SoundType.WOOD)));

    public static final Block TAVERN_HEARTH = register("tavern_hearth", new TavernHearthBlock(
        BlockBehaviour.Properties.of()
            .mapColor(MapColor.STONE)
            .strength(3.5f)
            .lightLevel(state -> 13)
            .sound(SoundType.STONE)));

    private UVBlocks() {
    }

    private static Block register(String name, Block block) {
        ResourceLocation id = UndergroundVillages.id(name);
        Registry.register(BuiltInRegistries.BLOCK, id, block);
        Registry.register(BuiltInRegistries.ITEM, id, new BlockItem(block, new Item.Properties()));
        return block;
    }

    public static void init() {
        // Triggers static registration.
    }
}
