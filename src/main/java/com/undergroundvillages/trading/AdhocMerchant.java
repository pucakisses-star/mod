package com.undergroundvillages.trading;

import java.util.function.Consumer;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.trading.Merchant;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import org.jetbrains.annotations.Nullable;

/**
 * A lightweight {@link Merchant} implementation that lets any {@link LivingEntity}
 * offer a fixed set of trades without being a villager. Used for pacified witches
 * and the Collector. A fresh instance is created per interaction; the offers list
 * is owned by the host so trade uses persist across sessions.
 */
public class AdhocMerchant implements Merchant {
    private final LivingEntity host;
    private final MerchantOffers offers;
    @Nullable
    private Player tradingPlayer;
    @Nullable
    private Consumer<MerchantOffer> tradeCallback;
    private int xp;

    public AdhocMerchant(LivingEntity host, MerchantOffers offers) {
        this.host = host;
        this.offers = offers;
    }

    /**
     * Sets a callback invoked after every completed trade, receiving the offer that was used.
     */
    public void setTradeCallback(@Nullable Consumer<MerchantOffer> tradeCallback) {
        this.tradeCallback = tradeCallback;
    }

    /**
     * Opens the trading screen for the given player with this merchant's offers.
     */
    public void open(ServerPlayer player, Component title) {
        this.setTradingPlayer(player);
        this.openTradingScreen(player, title, 1);
    }

    @Override
    public void setTradingPlayer(@Nullable Player player) {
        this.tradingPlayer = player;
    }

    @Override
    @Nullable
    public Player getTradingPlayer() {
        return this.tradingPlayer;
    }

    @Override
    public MerchantOffers getOffers() {
        return this.offers;
    }

    @Override
    public void overrideOffers(MerchantOffers offers) {
        // Offers are fixed and owned by the host entity; client-side sync is handled by the menu.
    }

    @Override
    public void notifyTrade(MerchantOffer offer) {
        offer.increaseUses();
        if (this.tradeCallback != null) {
            this.tradeCallback.accept(offer);
        }
        this.host.playSound(this.getNotifyTradeSound(), 1.0f, 1.0f);
    }

    @Override
    public void notifyTradeUpdated(ItemStack stack) {
    }

    @Override
    public int getVillagerXp() {
        return this.xp;
    }

    @Override
    public void overrideXp(int xp) {
        this.xp = xp;
    }

    @Override
    public boolean showProgressBar() {
        return false;
    }

    @Override
    public SoundEvent getNotifyTradeSound() {
        return SoundEvents.VILLAGER_YES;
    }

    @Override
    public boolean isClientSide() {
        return this.host.level().isClientSide;
    }
}
