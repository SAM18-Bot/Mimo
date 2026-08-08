package com.mimo.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface DailyStatsDao {
    @Query("SELECT * FROM daily_stats WHERE date = :date LIMIT 1")
    fun getByDateFlow(date: String): Flow<DailyStatsEntity?>

    @Query("SELECT * FROM daily_stats WHERE date = :date LIMIT 1")
    suspend fun getByDate(date: String): DailyStatsEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRaw(stats: DailyStatsEntity)

    @Transaction
    suspend fun insertOrUpdate(stats: DailyStatsEntity) {
        val existing = getByDate(stats.date)
        if (existing != null && !existing.isSynced && stats.isSynced) {
            // Unsynced local modification exists; do not overwrite with remote synced stats.
            return
        }
        insertRaw(stats)
    }

    @Query("SELECT * FROM daily_stats WHERE is_synced = 0")
    suspend fun getUnsynced(): List<DailyStatsEntity>

    @Query("UPDATE daily_stats SET is_synced = 1 WHERE date IN (:dates)")
    suspend fun markSynced(dates: List<String>)
}
