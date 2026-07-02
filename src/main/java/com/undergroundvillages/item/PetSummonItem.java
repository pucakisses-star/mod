package com.undergroundvillages.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.animal.Cat;
import net.minecraft.world.entity.animal.Parrot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;

/**
 * Tavern keeper pet items (Wolf Whistle, Cat Bell, Parrot Cracker). Using one
 * on the ground spawns the corresponding pet, already tamed by the user, and
 * consumes the item.
 */
public class PetSummonItem extends Item {
    public enum Kind {
        WOLF,
        CAT,
        PARROT
    }

    private final Kind kind;

    public PetSummonItem(Kind kind, Item.Properties properties) {
        super(properties);
        this.kind = kind;
    }

    @Override
    public InteractionResult useOn(UseOnContext ctx) {
        Level level = ctx.getLevel();
        Player player = ctx.getPlayer();
        if (player == null) {
            return InteractionResult.PASS;
        }
        if (!level.isClientSide) {
            BlockPos spawnPos = ctx.getClickedPos().above();
            RandomSource random = level.getRandom();

            TamableAnimal pet = switch (this.kind) {
                case WOLF -> EntityType.WOLF.create(level);
                case CAT -> EntityType.CAT.create(level);
                case PARROT -> EntityType.PARROT.create(level);
            };
            if (pet == null) {
                return InteractionResult.FAIL;
            }

            pet.moveTo(spawnPos.getX() + 0.5, spawnPos.getY(), spawnPos.getZ() + 0.5,
                random.nextFloat() * 360.0f, 0.0f);
            pet.tame(player);
            if (pet instanceof Cat cat) {
                level.registryAccess().registryOrThrow(Registries.CAT_VARIANT)
                    .getRandom(random)
                    .ifPresent(cat::setVariant);
            } else if (pet instanceof Parrot parrot) {
                parrot.setVariant(Parrot.Variant.byId(random.nextInt(5)));
            }
            pet.setPersistenceRequired();
            level.addFreshEntity(pet);

            level.playSound(null, spawnPos, this.happySound(), SoundSource.NEUTRAL,
                1.0f, 0.9f + random.nextFloat() * 0.2f);

            if (!player.getAbilities().instabuild) {
                ctx.getItemInHand().shrink(1);
            }
        }
        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    private SoundEvent happySound() {
        return switch (this.kind) {
            case WOLF -> SoundEvents.WOLF_WHINE;
            case CAT -> SoundEvents.CAT_PURREOW;
            case PARROT -> SoundEvents.PARROT_AMBIENT;
        };
    }
}
