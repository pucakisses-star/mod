package com.undergroundvillages.entity;

import java.util.EnumSet;
import java.util.UUID;

import com.undergroundvillages.tavern.Pacification;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.boss.wither.WitherBoss;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import org.jetbrains.annotations.Nullable;

/**
 * A hireable tavern bodyguard. Pay 30 emeralds and the mercenary follows the hirer
 * and fights hostile mobs near them (like an iron golem) for three in-game days
 * (72000 ticks). When the contract expires it walks (or teleports) back home to the
 * tavern and waits to be re-hired. Never attacks players or pacified tavern patrons.
 */
public class MercenaryEntity extends PathfinderMob {
    public static final int HIRE_COST_EMERALDS = 30;
    public static final long HIRE_DURATION_TICKS = 72000L;
    private static final int HIRE_DURATION_DAYS = 3;
    private static final long TICKS_PER_INGAME_HOUR = 1000L;

    @Nullable
    private UUID employer;
    private long expiry;
    @Nullable
    private BlockPos homePos;

    public MercenaryEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 40.0)
                .add(Attributes.MOVEMENT_SPEED, 0.33)
                .add(Attributes.ATTACK_DAMAGE, 6.0)
                .add(Attributes.FOLLOW_RANGE, 48.0);
    }

    public boolean isHired() {
        return this.employer != null && this.level().getGameTime() <= this.expiry;
    }

    @Nullable
    private Player getEmployerPlayer() {
        if (this.employer == null) {
            return null;
        }
        return this.level().getPlayerByUUID(this.employer);
    }

    /**
     * True if the given entity is within {@code range} blocks of the employer
     * (falling back to this mercenary if the employer is not resolvable here).
     */
    private boolean employerWithin(LivingEntity entity, double range) {
        Player employerPlayer = this.getEmployerPlayer();
        LivingEntity anchor = employerPlayer != null ? employerPlayer : this;
        return entity.distanceToSqr(anchor) <= range * range;
    }

    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(2, new MeleeAttackGoal(this, 1.25, true));
        this.goalSelector.addGoal(3, new FollowEmployerGoal());
        this.goalSelector.addGoal(4, new ReturnHomeGoal());
        this.goalSelector.addGoal(5, new WaterAvoidingRandomStrollGoal(this, 0.6));
        this.goalSelector.addGoal(6, new LookAtPlayerGoal(this, Player.class, 8.0f));
        this.goalSelector.addGoal(7, new RandomLookAroundGoal(this));

        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Monster.class, 10, true, false,
                (LivingEntity e) -> this.isHired()
                        && !Pacification.isPacified(e)
                        && !(e instanceof WitherBoss)
                        && this.employerWithin(e, 16.0)));
    }

    @Override
    public void setTarget(@Nullable LivingEntity target) {
        if (target instanceof Player) {
            // Mercenaries never fight players, no matter who hit them.
            return;
        }
        super.setTarget(target);
    }

    @Override
    public void tick() {
        super.tick();
        if (!this.level().isClientSide) {
            if (this.homePos == null) {
                this.homePos = this.blockPosition();
            }
            if (this.employer != null && this.level().getGameTime() > this.expiry) {
                if (this.level() instanceof ServerLevel serverLevel) {
                    ServerPlayer employerPlayer = serverLevel.getServer().getPlayerList().getPlayer(this.employer);
                    if (employerPlayer != null) {
                        employerPlayer.displayClientMessage(
                                Component.translatable("message.undergroundvillages.mercenary_expired"), false);
                    }
                }
                this.employer = null;
            }
        }
    }

    @Override
    protected InteractionResult mobInteract(Player player, InteractionHand hand) {
        if (!this.level().isClientSide) {
            if (this.employer != null && !this.employer.equals(player.getUUID())) {
                player.displayClientMessage(
                        Component.translatable("message.undergroundvillages.mercenary_busy"), true);
                this.playSound(SoundEvents.VILLAGER_NO, 1.0f, 1.0f);
            } else if (this.employer != null) {
                long remainingTicks = Math.max(0L, this.expiry - this.level().getGameTime());
                long hours = (remainingTicks + TICKS_PER_INGAME_HOUR - 1L) / TICKS_PER_INGAME_HOUR;
                player.displayClientMessage(
                        Component.literal("Hired: " + hours + " in-game hour" + (hours == 1L ? "" : "s") + " remaining"),
                        true);
            } else {
                ItemStack held = player.getItemInHand(hand);
                if (held.is(Items.EMERALD) && held.getCount() >= HIRE_COST_EMERALDS) {
                    if (!player.getAbilities().instabuild) {
                        held.shrink(HIRE_COST_EMERALDS);
                    }
                    this.employer = player.getUUID();
                    this.expiry = this.level().getGameTime() + HIRE_DURATION_TICKS;
                    this.playSound(SoundEvents.VILLAGER_YES, 1.0f, 1.0f);
                    player.displayClientMessage(
                            Component.translatable("message.undergroundvillages.mercenary_hired", HIRE_DURATION_DAYS),
                            false);
                } else {
                    player.displayClientMessage(
                            Component.translatable("message.undergroundvillages.mercenary_cost"), true);
                }
            }
        }
        return InteractionResult.sidedSuccess(this.level().isClientSide);
    }

    @Override
    @Nullable
    public SpawnGroupData finalizeSpawn(ServerLevelAccessor level, DifficultyInstance difficulty,
            MobSpawnType spawnType, @Nullable SpawnGroupData spawnData) {
        if (this.homePos == null) {
            this.homePos = this.blockPosition();
        }
        return super.finalizeSpawn(level, difficulty, spawnType, spawnData);
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        if (this.employer != null) {
            tag.putUUID("Employer", this.employer);
        }
        tag.putLong("Expiry", this.expiry);
        if (this.homePos != null) {
            tag.putIntArray("Home", new int[]{this.homePos.getX(), this.homePos.getY(), this.homePos.getZ()});
        }
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        this.employer = tag.hasUUID("Employer") ? tag.getUUID("Employer") : null;
        this.expiry = tag.getLong("Expiry");
        if (tag.contains("Home", Tag.TAG_INT_ARRAY)) {
            int[] home = tag.getIntArray("Home");
            if (home.length == 3) {
                this.homePos = new BlockPos(home[0], home[1], home[2]);
            }
        }
    }

    @Override
    public boolean removeWhenFarAway(double distanceToClosestPlayer) {
        return false;
    }

    /**
     * While hired, keeps the mercenary near its employer; teleports beside them
     * if it falls more than 32 blocks behind.
     */
    private class FollowEmployerGoal extends Goal {
        private static final double START_DISTANCE_SQR = 25.0;   // > 5 blocks
        private static final double TELEPORT_DISTANCE_SQR = 1024.0; // > 32 blocks

        @Nullable
        private Player employerPlayer;
        private int repathCooldown;

        FollowEmployerGoal() {
            this.setFlags(EnumSet.of(Goal.Flag.MOVE));
        }

        @Override
        public boolean canUse() {
            if (!MercenaryEntity.this.isHired()) {
                return false;
            }
            Player p = MercenaryEntity.this.getEmployerPlayer();
            if (p == null || p.level() != MercenaryEntity.this.level()) {
                return false;
            }
            if (MercenaryEntity.this.distanceToSqr(p) <= START_DISTANCE_SQR) {
                return false;
            }
            this.employerPlayer = p;
            return true;
        }

        @Override
        public void start() {
            this.repathCooldown = 0;
        }

        @Override
        public void tick() {
            Player p = this.employerPlayer;
            if (p == null) {
                return;
            }
            MercenaryEntity.this.getLookControl().setLookAt(p, 10.0f, MercenaryEntity.this.getMaxHeadXRot());
            if (--this.repathCooldown <= 0) {
                this.repathCooldown = this.adjustedTickDelay(10);
                MercenaryEntity.this.getNavigation().moveTo(p, 1.15);
            }
            if (MercenaryEntity.this.distanceToSqr(p) > TELEPORT_DISTANCE_SQR) {
                double dx = MercenaryEntity.this.getRandom().nextInt(3) - 1;
                double dz = MercenaryEntity.this.getRandom().nextInt(3) - 1;
                MercenaryEntity.this.teleportTo(p.getX() + dx, p.getY(), p.getZ() + dz);
                MercenaryEntity.this.getNavigation().stop();
            }
        }

        @Override
        public void stop() {
            this.employerPlayer = null;
            MercenaryEntity.this.getNavigation().stop();
        }
    }

    /**
     * When the contract is over, walks back to the home position recorded at spawn;
     * teleports home if pathing gives up while still far away.
     */
    private class ReturnHomeGoal extends Goal {
        private static final double ARRIVE_DISTANCE_SQR = 9.0;      // within 3 blocks = home
        private static final double TELEPORT_DISTANCE_SQR = 9216.0; // 96 blocks

        private int repathCooldown;

        ReturnHomeGoal() {
            this.setFlags(EnumSet.of(Goal.Flag.MOVE));
        }

        @Override
        public boolean canUse() {
            if (MercenaryEntity.this.isHired()) {
                return false;
            }
            BlockPos home = MercenaryEntity.this.homePos;
            return home != null && MercenaryEntity.this.blockPosition().distSqr(home) > ARRIVE_DISTANCE_SQR;
        }

        @Override
        public void start() {
            this.repathCooldown = 0;
        }

        @Override
        public void tick() {
            BlockPos home = MercenaryEntity.this.homePos;
            if (home == null) {
                return;
            }
            if (--this.repathCooldown <= 0) {
                this.repathCooldown = this.adjustedTickDelay(20);
                MercenaryEntity.this.getNavigation()
                        .moveTo(home.getX() + 0.5, home.getY(), home.getZ() + 0.5, 0.9);
            }
            if (MercenaryEntity.this.getNavigation().isDone()
                    && MercenaryEntity.this.blockPosition().distSqr(home) > TELEPORT_DISTANCE_SQR) {
                MercenaryEntity.this.teleportTo(home.getX() + 0.5, home.getY(), home.getZ() + 0.5);
            }
        }

        @Override
        public void stop() {
            MercenaryEntity.this.getNavigation().stop();
        }
    }
}
