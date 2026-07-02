package com.undergroundvillages.entity;

import com.undergroundvillages.raid.RaidEmpowermentData;
import com.undergroundvillages.trading.AdhocMerchant;
import com.undergroundvillages.trading.CollectorTrades;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.MerchantOffers;
import net.minecraft.world.level.Level;
import org.jetbrains.annotations.Nullable;

/**
 * The Collector: a non-hostile illager found in taverns who pays a fortune in
 * emeralds for Nether Stars and Dragon Heads. Every big deal (48+ emeralds paid
 * out) empowers the illagers: one pending raid empowerment is added to the level.
 */
public class CollectorEntity extends PathfinderMob {
    private static final int EMPOWERING_PAYOUT_THRESHOLD = 48;

    @Nullable
    private MerchantOffers offers;

    public CollectorEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 24.0)
                .add(Attributes.MOVEMENT_SPEED, 0.3);
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(5, new WaterAvoidingRandomStrollGoal(this, 0.5));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 8.0f));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));
    }

    private MerchantOffers getOrCreateOffers() {
        if (this.offers == null) {
            this.offers = CollectorTrades.createOffers();
        }
        return this.offers;
    }

    @Override
    protected InteractionResult mobInteract(Player player, InteractionHand hand) {
        if (!this.level().isClientSide && player instanceof ServerPlayer serverPlayer) {
            AdhocMerchant merchant = new AdhocMerchant(this, this.getOrCreateOffers());
            merchant.setTradeCallback(offer -> {
                if (offer.getResult().is(Items.EMERALD)
                        && offer.getResult().getCount() >= EMPOWERING_PAYOUT_THRESHOLD) {
                    RaidEmpowermentData.get((ServerLevel) this.level()).empower();
                    Player tradingPlayer = merchant.getTradingPlayer();
                    if (tradingPlayer != null) {
                        tradingPlayer.displayClientMessage(
                                Component.translatable("message.undergroundvillages.collector_deal"), false);
                    }
                    this.playSound(SoundEvents.EVOKER_CELEBRATE);
                }
            });
            merchant.open(serverPlayer, this.getDisplayName());
        }
        return InteractionResult.sidedSuccess(this.level().isClientSide);
    }

    @Override
    public boolean removeWhenFarAway(double distanceToClosestPlayer) {
        return false;
    }
}
