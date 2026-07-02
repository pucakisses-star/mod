package com.undergroundvillages.light;

import com.undergroundvillages.item.MiningHatItem;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

import org.jetbrains.annotations.Nullable;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Server-side manager for the Mining Hat's head light. While a player wears the
 * hat, an invisible {@code minecraft:light} block (level 13) follows their eye
 * position; it is cleaned up when they move, unequip the hat, die, switch
 * dimension or disconnect. Water sources get a waterlogged light and are
 * restored on removal. Other blocks are never overwritten.
 */
public final class MiningHatLight {
    private static final int LIGHT_LEVEL = 13;
    private static final Map<UUID, GlobalPos> LAST = new HashMap<>();

    private MiningHatLight() {
    }

    public static void init() {
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                tickPlayer(server, player);
            }
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            GlobalPos last = LAST.remove(handler.getPlayer().getUUID());
            if (last != null) {
                removeLight(server, last);
            }
        });
    }

    private static void tickPlayer(MinecraftServer server, ServerPlayer player) {
        boolean wearing = player.getItemBySlot(EquipmentSlot.HEAD).getItem() instanceof MiningHatItem
            && !player.isSpectator() && player.isAlive();
        UUID id = player.getUUID();
        GlobalPos last = LAST.get(id);

        if (!wearing) {
            if (last != null) {
                LAST.remove(id);
                removeLight(server, last);
            }
            return;
        }

        ServerLevel level = player.serverLevel();
        BlockPos desired = BlockPos.containing(player.getEyePosition());
        if (last != null && last.dimension() == level.dimension() && last.pos().equals(desired)) {
            return;
        }

        boolean placed = placeLight(level, desired);
        if (last != null) {
            removeLight(server, last);
        }
        if (placed) {
            LAST.put(id, GlobalPos.of(level.dimension(), desired.immutable()));
        } else {
            // Target position was blocked; clear so we retry next tick.
            LAST.remove(id);
        }
    }

    /**
     * Places a level-13 light block at {@code pos} if the position is air, a
     * water source (waterlogged light) or already a light block. Never
     * overwrites any other block.
     */
    private static boolean placeLight(ServerLevel level, BlockPos pos) {
        if (!level.isLoaded(pos)) {
            return false;
        }
        BlockState existing = level.getBlockState(pos);
        if (existing.is(Blocks.LIGHT)) {
            boolean waterlogged = existing.getValue(BlockStateProperties.WATERLOGGED);
            level.setBlock(pos, lightState(waterlogged), 3);
            return true;
        }
        if (existing.isAir()) {
            level.setBlock(pos, lightState(false), 3);
            return true;
        }
        if (existing.is(Blocks.WATER) && existing.getFluidState().isSource()) {
            level.setBlock(pos, lightState(true), 3);
            return true;
        }
        return false;
    }

    private static BlockState lightState(boolean waterlogged) {
        return Blocks.LIGHT.defaultBlockState()
            .setValue(LightBlock.LEVEL, LIGHT_LEVEL)
            .setValue(BlockStateProperties.WATERLOGGED, waterlogged);
    }

    /**
     * Removes a previously placed light, restoring water if it was waterlogged.
     * Only ever removes {@code minecraft:light} blocks.
     */
    private static void removeLight(MinecraftServer server, @Nullable GlobalPos globalPos) {
        if (globalPos == null) {
            return;
        }
        ServerLevel level = server.getLevel(globalPos.dimension());
        if (level == null) {
            return;
        }
        BlockPos pos = globalPos.pos();
        if (!level.isLoaded(pos)) {
            return;
        }
        BlockState state = level.getBlockState(pos);
        if (!state.is(Blocks.LIGHT)) {
            return;
        }
        boolean waterlogged = state.getValue(BlockStateProperties.WATERLOGGED);
        level.setBlock(pos, waterlogged ? Blocks.WATER.defaultBlockState() : Blocks.AIR.defaultBlockState(), 3);
    }
}
