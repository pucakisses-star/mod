package com.undergroundvillages.raid;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

import java.util.HashSet;
import java.util.Set;

/**
 * Per-level persistent state tracking raid empowerments bought from the Collector.
 * <p>
 * Each completed Collector deal calls {@link #empower()}, adding one pending empowerment.
 * When a raider joins a raid, {@link #isOrBecomesEmpowered(int)} either recognises an
 * already-empowered raid or consumes one pending empowerment and marks that raid id.
 */
public class RaidEmpowermentData extends SavedData {
    private static final String STORAGE_NAME = "undergroundvillages_raid_empowerment";
    private static final String TAG_PENDING = "Pending";
    private static final String TAG_EMPOWERED_RAIDS = "EmpoweredRaids";

    public static final SavedData.Factory<RaidEmpowermentData> FACTORY =
            new SavedData.Factory<>(RaidEmpowermentData::new, RaidEmpowermentData::load, null);

    private int pending;
    private final Set<Integer> empoweredRaidIds = new HashSet<>();

    public static RaidEmpowermentData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(FACTORY, STORAGE_NAME);
    }

    /**
     * Queues one raid empowerment (called after every completed Collector deal).
     */
    public void empower() {
        this.pending++;
        this.setDirty();
    }

    /**
     * Returns whether the given raid is empowered. If it is not yet empowered but there
     * is a pending empowerment, one is consumed and the raid becomes (permanently) empowered.
     */
    public boolean isOrBecomesEmpowered(int raidId) {
        if (this.empoweredRaidIds.contains(raidId)) {
            return true;
        }
        if (this.pending > 0) {
            this.pending--;
            this.empoweredRaidIds.add(raidId);
            this.setDirty();
            return true;
        }
        return false;
    }

    @Override
    public CompoundTag save(CompoundTag tag, HolderLookup.Provider registries) {
        tag.putInt(TAG_PENDING, this.pending);
        int[] raidIds = new int[this.empoweredRaidIds.size()];
        int i = 0;
        for (int raidId : this.empoweredRaidIds) {
            raidIds[i++] = raidId;
        }
        tag.putIntArray(TAG_EMPOWERED_RAIDS, raidIds);
        return tag;
    }

    public static RaidEmpowermentData load(CompoundTag tag, HolderLookup.Provider registries) {
        RaidEmpowermentData data = new RaidEmpowermentData();
        data.pending = tag.getInt(TAG_PENDING);
        for (int raidId : tag.getIntArray(TAG_EMPOWERED_RAIDS)) {
            data.empoweredRaidIds.add(raidId);
        }
        return data;
    }
}
