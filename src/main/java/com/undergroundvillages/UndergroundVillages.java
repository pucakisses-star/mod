package com.undergroundvillages;

import net.fabricmc.api.ModInitializer;
import net.minecraft.resources.ResourceLocation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class UndergroundVillages implements ModInitializer {
    public static final String MOD_ID = "undergroundvillages";
    public static final Logger LOGGER = LoggerFactory.getLogger("Underground Villages");

    public static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(MOD_ID, path);
    }

    @Override
    public void onInitialize() {
        LOGGER.info("Underground Villages initializing");
    }
}
