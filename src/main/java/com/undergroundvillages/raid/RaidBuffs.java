package com.undergroundvillages.raid;

import com.undergroundvillages.UndergroundVillages;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Pillager;
import net.minecraft.world.entity.monster.Vindicator;
import net.minecraft.world.entity.raid.Raider;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;

/**
 * Buffs applied to every raider joining an empowered raid: +10 max health (healed),
 * infinite Speed I + Resistance I, and enchanted gear for vindicators and pillagers.
 */
public final class RaidBuffs {
    private static final ResourceLocation HEALTH_MODIFIER_ID = UndergroundVillages.id("raid_empowerment");
    private static final double HEALTH_BONUS = 10.0;
    private static final float EQUIPMENT_DROP_CHANCE = 0.045f;

    private RaidBuffs() {
    }

    public static void apply(Raider raider) {
        AttributeInstance maxHealth = raider.getAttribute(Attributes.MAX_HEALTH);
        if (maxHealth != null && maxHealth.getModifier(HEALTH_MODIFIER_ID) == null) {
            maxHealth.addPermanentModifier(new AttributeModifier(
                    HEALTH_MODIFIER_ID, HEALTH_BONUS, AttributeModifier.Operation.ADD_VALUE));
        }
        raider.heal(10.0f);

        raider.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, MobEffectInstance.INFINITE_DURATION, 0));
        raider.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, MobEffectInstance.INFINITE_DURATION, 0));

        if (raider instanceof Vindicator) {
            ItemStack axe = new ItemStack(Items.DIAMOND_AXE);
            axe.enchant(enchantment(raider, Enchantments.SHARPNESS), 3);
            raider.setItemSlot(EquipmentSlot.MAINHAND, axe);
            raider.setDropChance(EquipmentSlot.MAINHAND, EQUIPMENT_DROP_CHANCE);
        } else if (raider instanceof Pillager) {
            ItemStack crossbow = new ItemStack(Items.CROSSBOW);
            crossbow.enchant(enchantment(raider, Enchantments.QUICK_CHARGE), 2);
            crossbow.enchant(enchantment(raider, Enchantments.PIERCING), 2);
            raider.setItemSlot(EquipmentSlot.MAINHAND, crossbow);
            raider.setDropChance(EquipmentSlot.MAINHAND, EQUIPMENT_DROP_CHANCE);
        }
    }

    private static Holder<Enchantment> enchantment(Raider raider, ResourceKey<Enchantment> key) {
        return raider.level().registryAccess().registryOrThrow(Registries.ENCHANTMENT).getHolderOrThrow(key);
    }
}
