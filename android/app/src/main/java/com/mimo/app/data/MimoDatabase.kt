package com.mimo.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [AssignmentEntity::class, DailyStatsEntity::class],
    version = 1,
    exportSchema = false
)
abstract class MimoDatabase : RoomDatabase() {
    abstract fun assignmentDao(): AssignmentDao
    abstract fun dailyStatsDao(): DailyStatsDao

    companion object {
        @Volatile
        private var INSTANCE: MimoDatabase? = null

        fun getDatabase(context: Context): MimoDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    MimoDatabase::class.java,
                    "mimo_database"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
