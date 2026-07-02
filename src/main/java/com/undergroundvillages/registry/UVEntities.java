package com.undergroundvillages.registry;

import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.entity.CollectorEntity;
import com.undergroundvillages.entity.MercenaryEntity;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;

public final class UVEntities {
    public static final EntityType<MercenaryEntity> MERCENARY = Registry.register(
            BuiltInRegistries.ENTITY_TYPE,
            UndergroundVillages.id("mercenary"),
            EntityType.Builder.of(MercenaryEntity::new, MobCategory.CREATURE)
                    .sized(0.6f, 1.95f)
                    .clientTrackingRange(10)
                    .build(null));

    public static final EntityType<CollectorEntity> COLLECTOR = Registry.register(
            BuiltInRegistries.ENTITY_TYPE,
            UndergroundVillages.id("collector"),
            EntityType.Builder.of(CollectorEntity::new, MobCategory.CREATURE)
                    .sized(0.6f, 1.95f)
                    .clientTrackingRange(10)
                    .build(null));

    private UVEntities() {
    }

    public static void init() {
        FabricDefaultAttributeRegistry.register(MERCENARY, MercenaryEntity.createAttributes());
        FabricDefaultAttributeRegistry.register(COLLECTOR, CollectorEntity.createAttributes());
    }
}
