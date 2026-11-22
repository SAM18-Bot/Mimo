package com.mimo.app.data

import android.content.Context
import android.util.Base64
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.mimo.app.network.ApiClient
import java.security.MessageDigest
import org.json.JSONObject

@Database(
    entities = [AssignmentEntity::class, DailyStatsEntity::class, PendingUsage::class],
    version = 4,
    exportSchema = false
)
abstract class MimoDatabase : RoomDatabase() {
    abstract fun assignmentDao(): AssignmentDao
    abstract fun dailyStatsDao(): DailyStatsDao

    companion object {
        private val instances = mutableMapOf<String, MimoDatabase>()
        private val addPendingUsage = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS pending_usage (" +
                        "id TEXT NOT NULL PRIMARY KEY, date TEXT NOT NULL, category TEXT NOT NULL)"
                )
            }
        }

        private val addSyncDetails = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE assignments ADD COLUMN request_id TEXT")
                db.execSQL("UPDATE assignments SET request_id = lower(hex(randomblob(16))) WHERE id < 0")
                db.execSQL("ALTER TABLE pending_usage ADD COLUMN app_name TEXT")
            }
        }

        private val addDeadlineTime = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE assignments ADD COLUMN due_time TEXT")
            }
        }

        fun accountNamespace(token: String?, server: String): String {
            // The subject is only a local cache namespace. The server still validates the token.
            val subject = runCatching {
                val claims = Base64.decode(token!!.split('.')[1], Base64.URL_SAFE)
                JSONObject(claims.toString(Charsets.UTF_8)).getString("sub").toLong()
            }.getOrNull()
            return if (subject == null) "signed_out" else {
                val origin = MessageDigest.getInstance("SHA-256").digest(server.toByteArray())
                    .joinToString("") { "%02x".format(it) }
                "${origin}_$subject"
            }
        }

        @Synchronized
        fun getDatabase(
            context: Context,
            token: String? = TokenManager.getToken(context),
            server: String = ApiClient.baseUrl,
        ): MimoDatabase {
            val key = accountNamespace(token, server)
            // The old shared database has no account ownership metadata. Leave it
            // alone rather than expose its contents to whichever account logs in next.
            return instances.getOrPut(key) {
                Room.databaseBuilder(context.applicationContext, MimoDatabase::class.java, "mimo_database_$key")
                    .addMigrations(addPendingUsage, addDeadlineTime, addSyncDetails)
                    .build()
            }
        }
    }
}
