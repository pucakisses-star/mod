package com.undergroundvillages;

import com.undergroundvillages.light.MiningHatLight;
import com.undergroundvillages.registry.UVBlockEntities;
import com.undergroundvillages.registry.UVBlocks;
import com.undergroundvillages.registry.UVEntities;
import com.undergroundvillages.registry.UVItems;
import com.undergroundvillages.registry.UVVillagers;
import com.undergroundvillages.trading.WitchTrading;
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
        UVBlocks.init();
        UVBlockEntities.init();
        UVEntities.init();
        UVItems.init();
        UVVillagers.init();
        MiningHatLight.init();
        WitchTrading.init();
        LOGGER.info("Underground Villages initialized — the caves are inhabited.");
    }
}
