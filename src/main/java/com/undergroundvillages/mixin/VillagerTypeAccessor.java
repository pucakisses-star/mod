package com.undergroundvillages.mixin;

import java.util.Map;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.npc.VillagerType;
import net.minecraft.world.level.biome.Biome;

/**
 * Exposes the private static {@code VillagerType.BY_BIOME} map (a mutable
 * HashMap built via {@code Util.make}) so that custom villager types can be
 * associated with biomes at mod initialization.
 */
@Mixin(VillagerType.class)
public interface VillagerTypeAccessor {
    @Accessor("BY_BIOME")
    static Map<ResourceKey<Biome>, VillagerType> getByBiome() {
        throw new AssertionError();
    }
}
