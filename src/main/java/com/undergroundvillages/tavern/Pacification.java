package com.undergroundvillages.tavern;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;

/**
 * Central helper for the tavern pacification mechanic. Pacified mobs carry the
 * {@value #TAG} command tag (persisted with the entity) and never target players
 * again — see {@code MobSetTargetMixin}.
 */
public final class Pacification {
    public static final String TAG = "uv_pacified";

    private Pacification() {
    }

    public static boolean isPacified(Entity e) {
        return e.getTags().contains(TAG);
    }

    public static void pacify(Mob mob) {
        mob.addTag(TAG);
        mob.setTarget(null);
        mob.setAggressive(false);
        mob.setPersistenceRequired();
        if (mob instanceof NeutralMob n) {
            n.setRemainingPersistentAngerTime(0);
            n.setPersistentAngerTarget(null);
        }
    }
}
