package com.undergroundvillages.mixin;

import com.undergroundvillages.tavern.Pacification;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import org.jetbrains.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Prevents pacified mobs (tagged {@link Pacification#TAG} by the Tavern Hearth) from ever
 * targeting players again, even far away from the tavern. Non-player targets are unaffected,
 * so pacified mobs can still defend themselves against other mobs.
 */
@Mixin(Mob.class)
public abstract class MobSetTargetMixin {
    @Inject(method = "setTarget", at = @At("HEAD"), cancellable = true)
    private void undergroundvillages$blockPacifiedTargeting(@Nullable LivingEntity target, CallbackInfo ci) {
        if (target instanceof Player && ((Mob) (Object) this).getTags().contains(Pacification.TAG)) {
            ci.cancel();
        }
    }
}
