package com.undergroundvillages.client.render;

import com.undergroundvillages.UndergroundVillages;
import com.undergroundvillages.entity.MercenaryEntity;
import net.minecraft.client.model.VillagerModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.resources.ResourceLocation;

public class MercenaryRenderer extends MobRenderer<MercenaryEntity, VillagerModel<MercenaryEntity>> {
    private static final ResourceLocation TEXTURE = UndergroundVillages.id("textures/entity/mercenary.png");

    public MercenaryRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new VillagerModel<>(ctx.bakeLayer(ModelLayers.VILLAGER)), 0.5f);
    }

    @Override
    public ResourceLocation getTextureLocation(MercenaryEntity entity) {
        return TEXTURE;
    }
}
