package com.mimo.app.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.mimo.app.data.MimoDatabase
import com.mimo.app.data.toEntity
import com.mimo.app.network.ApiClient
import com.mimo.app.network.SyncPayload
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

class SyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val db = MimoDatabase.getDatabase(applicationContext)
            val statsDao = db.dailyStatsDao()
            val assignmentDao = db.assignmentDao()

            val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
            val currentStats = statsDao.getByDate(today)

            // If we have unsynced stats, push them
            if (currentStats != null && !currentStats.isSynced) {
                val payload = SyncPayload(
                    date = today,
                    mobileProductiveMin = currentStats.productiveMin,
                    mobileDistractingMin = currentStats.distractingMin,
                    mobileNeutralMin = currentStats.neutralMin
                )

                // Push to PC
                ApiClient.api.pushSync(payload)
                
                // Mark as synced locally so we don't double count
                statsDao.insertOrUpdate(currentStats.copy(isSynced = true))
            }

            // Pull merged data from PC
            val pullData = ApiClient.api.pullSync()
            
            pullData.mergedStats?.let { remoteStats ->
                statsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))
            }
            
            val remoteAssignments = pullData.assignments
            if (remoteAssignments.isNotEmpty()) {
                assignmentDao.insertAll(remoteAssignments.map { it.toEntity(isSynced = true) })
            }

            Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            Result.retry()
        }
    }
}
