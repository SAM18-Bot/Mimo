package com.mimo.app.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mimo.app.network.DailyStats

@Entity(tableName = "daily_stats")
data class DailyStatsEntity(
    @PrimaryKey
    @ColumnInfo(name = "date")
    val date: String,

    @ColumnInfo(name = "productive_min")
    val productiveMin: Int = 0,

    @ColumnInfo(name = "distracting_min")
    val distractingMin: Int = 0,

    @ColumnInfo(name = "neutral_min")
    val neutralMin: Int = 0,

    @ColumnInfo(name = "focus_score")
    val focusScore: Double = 0.0,

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false
)

fun DailyStatsEntity.toDomain(): DailyStats {
    return DailyStats(
        date = date,
        productive_min = productiveMin,
        distracting_min = distractingMin,
        neutral_min = neutralMin,
        focus_score = focusScore,
        desk_time_min = productiveMin + distractingMin + neutralMin
    )
}

fun DailyStats.toEntity(isSynced: Boolean = false): DailyStatsEntity {
    return DailyStatsEntity(
        date = date,
        productiveMin = productive_min,
        distractingMin = distracting_min,
        neutralMin = neutral_min,
        focusScore = focus_score,
        isSynced = isSynced
    )
}
