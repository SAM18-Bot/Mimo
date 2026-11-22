package com.mimo.app.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "pending_usage")
data class PendingUsage(
    @PrimaryKey val id: String,
    val date: String,
    val category: String,
    @ColumnInfo(name = "app_name") val appName: String? = null,
)
