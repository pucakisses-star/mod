package com.undergroundvillages.mixin;

import com.undergroundvillages.raid.RaidBuffs;
import com.undergroundvillages.raid.RaidEmpowermentData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.raid.Raid;
import net.minecraft.world.entity.raid.Raider;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Applies Collector-bought empowerment buffs to raiders as they join a raid.
 * The first raider of a raid consumes one pending empowerment (marking the raid id);
 * every raider joining a marked raid receives {@link RaidBuffs}.
 */
@Mixin(Raid.class)
public abstract class RaidJoinMixin {
    @Shadow
    @Final
    private ServerLevel level;

    @Shadow
    @Final
    private int id;

    @Inject(
            method = "joinRaid(ILnet/minecraft/world/entity/raid/Raider;Lnet/minecraft/core/BlockPos;Z)V",
            at = @At("TAIL")
    )
    private void undergroundvillages$empower(int wave, Raider raider, BlockPos pos, boolean recruited, CallbackInfo ci) {
        if (RaidEmpowermentData.get(this.level).isOrBecomesEmpowered(this.id)) {
            RaidBuffs.apply(raider);
        }
    }
}
