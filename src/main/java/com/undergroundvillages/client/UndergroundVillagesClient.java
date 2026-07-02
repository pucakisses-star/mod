package com.undergroundvillages.client;

import com.undergroundvillages.client.render.CollectorRenderer;
import com.undergroundvillages.client.render.MercenaryRenderer;
import com.undergroundvillages.registry.UVEntities;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class UndergroundVillagesClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        EntityRendererRegistry.register(UVEntities.MERCENARY, MercenaryRenderer::new);
        EntityRendererRegistry.register(UVEntities.COLLECTOR, CollectorRenderer::new);
    }
}
