package com.undergroundvillages.trading;

import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;

/**
 * Offer factory for the Collector. The big emerald payouts (nether star, dragon head)
 * are the deals that empower the illagers' next raid; the callback that triggers the
 * empowerment lives in {@code CollectorEntity}.
 */
public final class CollectorTrades {
    private CollectorTrades() {
    }

    public static MerchantOffers createOffers() {
        MerchantOffers offers = new MerchantOffers();
        offers.add(new MerchantOffer(
                new ItemCost(Items.NETHER_STAR, 1),
                new ItemStack(Items.EMERALD, 48),
                3, 30, 0.05f));
        offers.add(new MerchantOffer(
                new ItemCost(Items.DRAGON_HEAD, 1),
                new ItemStack(Items.EMERALD, 64),
                1, 50, 0.05f));
        offers.add(new MerchantOffer(
                new ItemCost(Items.EMERALD, 16),
                new ItemStack(Items.OMINOUS_BOTTLE, 1),
                4, 5, 0.05f));
        return offers;
    }
}
