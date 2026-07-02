package com.undergroundvillages.item;

import com.undergroundvillages.UndergroundVillages;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * The Mining Hat: a light-emitting helmet sold by miner villagers. The actual
 * light emission is handled server-side by {@code MiningHatLight}, which places
 * and removes invisible {@code minecraft:light} blocks at the wearer's head.
 */
public class MiningHatItem extends ArmorItem {
    public static final Holder<ArmorMaterial> MATERIAL = registerMaterial();

    public MiningHatItem() {
        super(MATERIAL, ArmorItem.Type.HELMET,
            new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(15)));
    }

    private static Holder<ArmorMaterial> registerMaterial() {
        Map<ArmorItem.Type, Integer> defense = new EnumMap<>(ArmorItem.Type.class);
        defense.put(ArmorItem.Type.BOOTS, 0);
        defense.put(ArmorItem.Type.LEGGINGS, 0);
        defense.put(ArmorItem.Type.CHESTPLATE, 0);
        defense.put(ArmorItem.Type.HELMET, 2);
        defense.put(ArmorItem.Type.BODY, 0);
        return Registry.registerForHolder(
            BuiltInRegistries.ARMOR_MATERIAL,
            UndergroundVillages.id("mining_hat"),
            new ArmorMaterial(
                defense,
                12,
                SoundEvents.ARMOR_EQUIP_IRON,
                () -> Ingredient.of(Items.GOLD_INGOT),
                List.of(new ArmorMaterial.Layer(UndergroundVillages.id("mining_hat"))),
                0.0f,
                0.0f));
    }
}
