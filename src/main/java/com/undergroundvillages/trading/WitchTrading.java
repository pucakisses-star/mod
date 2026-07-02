package com.undergroundvillages.trading;

import com.undergroundvillages.tavern.Pacification;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.minecraft.core.Holder;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.monster.Witch;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.Potion;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.item.alchemy.Potions;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Right-clicking a pacified witch opens a potion shop. Offers are deterministic per witch
 * (seeded from its UUID): four distinct sell-potion offers priced 5-9 emeralds, plus two
 * buy offers for glass bottles and nether wart.
 */
public final class WitchTrading {
    private static final List<Holder<Potion>> POTION_POOL = List.of(
            Potions.HEALING,
            Potions.STRONG_HEALING,
            Potions.SWIFTNESS,
            Potions.FIRE_RESISTANCE,
            Potions.NIGHT_VISION,
            Potions.WATER_BREATHING,
            Potions.REGENERATION,
            Potions.STRENGTH
    );
    private static final int POTION_OFFER_COUNT = 4;

    private WitchTrading() {
    }

    public static void init() {
        UseEntityCallback.EVENT.register((player, world, hand, entity, hitResult) -> {
            if (hand != InteractionHand.MAIN_HAND
                    || player.isSpectator()
                    || !(entity instanceof Witch witch)
                    || !Pacification.isPacified(witch)
                    || !witch.isAlive()) {
                return InteractionResult.PASS;
            }
            if (!world.isClientSide && player instanceof ServerPlayer serverPlayer) {
                new AdhocMerchant(witch, buildOffers(witch)).open(serverPlayer, witch.getDisplayName());
            }
            return InteractionResult.SUCCESS;
        });
    }

    static MerchantOffers buildOffers(Witch witch) {
        UUID uuid = witch.getUUID();
        RandomSource random = RandomSource.create(uuid.getMostSignificantBits() ^ uuid.getLeastSignificantBits());

        MerchantOffers offers = new MerchantOffers();

        // Shuffle-pick four distinct potions from the pool.
        List<Holder<Potion>> pool = new ArrayList<>(POTION_POOL);
        for (int i = 0; i < POTION_OFFER_COUNT; i++) {
            Holder<Potion> potion = pool.remove(random.nextInt(pool.size()));
            int price = 5 + random.nextInt(5); // 5-9 emeralds
            offers.add(new MerchantOffer(
                    new ItemCost(Items.EMERALD, price),
                    PotionContents.createItemStack(Items.POTION, potion),
                    12, 5, 0.05f));
        }

        // Buy offers: brewing supplies for emeralds.
        offers.add(new MerchantOffer(
                new ItemCost(Items.GLASS_BOTTLE, 8), new ItemStack(Items.EMERALD), 16, 3, 0.05f));
        offers.add(new MerchantOffer(
                new ItemCost(Items.NETHER_WART, 6), new ItemStack(Items.EMERALD), 16, 3, 0.05f));

        return offers;
    }
}
