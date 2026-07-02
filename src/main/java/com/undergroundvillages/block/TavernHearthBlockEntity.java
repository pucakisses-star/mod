package com.undergroundvillages.block;

import com.undergroundvillages.registry.UVBlockEntities;
import com.undergroundvillages.tavern.Pacification;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.boss.wither.WitherBoss;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.List;

/**
 * Scans for hostile mobs around the hearth every 40 ticks and pacifies them.
 * Pacified mobs are tagged {@link Pacification#TAG}, made persistent and never
 * target players again.
 */
public class TavernHearthBlockEntity extends BlockEntity {
    private static final int SCAN_INTERVAL_TICKS = 40;
    private static final double RADIUS_XZ = 16.0;
    private static final double RADIUS_Y = 8.0;

    private int tickCounter;

    public TavernHearthBlockEntity(BlockPos pos, BlockState state) {
        super(UVBlockEntities.TAVERN_HEARTH, pos, state);
    }

    public static void serverTick(Level level, BlockPos pos, BlockState state, TavernHearthBlockEntity hearth) {
        if (!(level instanceof ServerLevel serverLevel)) {
            return;
        }
        if (++hearth.tickCounter < SCAN_INTERVAL_TICKS) {
            return;
        }
        hearth.tickCounter = 0;

        AABB box = new AABB(pos).inflate(RADIUS_XZ, RADIUS_Y, RADIUS_XZ);
        List<Mob> hostiles = level.getEntitiesOfClass(Mob.class, box,
            mob -> mob instanceof Enemy && !(mob instanceof WitherBoss) && !Pacification.isPacified(mob));

        for (Mob mob : hostiles) {
            Pacification.pacify(mob);
            serverLevel.sendParticles(ParticleTypes.HEART,
                mob.getX(), mob.getY() + mob.getBbHeight() + 0.5, mob.getZ(),
                5, 0.4, 0.4, 0.4, 0.02);
            serverLevel.playSound(null, mob.getX(), mob.getY(), mob.getZ(),
                SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.NEUTRAL, 0.35f, 1.0f);
        }
    }
}
