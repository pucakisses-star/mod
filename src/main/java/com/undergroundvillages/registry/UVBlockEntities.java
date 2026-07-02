package com.undergroundvillages.registry;

import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.block.TavernHearthBlockEntity;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.entity.BlockEntityType;

/**
 * Block entity types for Underground Villages.
 */
public final class UVBlockEntities {
    public static final BlockEntityType<TavernHearthBlockEntity> TAVERN_HEARTH = Registry.register(
        BuiltInRegistries.BLOCK_ENTITY_TYPE,
        UndergroundVillages.id("tavern_hearth"),
        BlockEntityType.Builder.of(TavernHearthBlockEntity::new, UVBlocks.TAVERN_HEARTH).build(null));

    private UVBlockEntities() {
    }

    public static void init() {
        // Triggers static registration.
    }
}
