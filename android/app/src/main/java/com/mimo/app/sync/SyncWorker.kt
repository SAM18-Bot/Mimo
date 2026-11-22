package com.mimo.app.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.mimo.app.data.MimoDatabase
import com.mimo.app.data.TokenManager
import com.mimo.app.data.toEntity
import com.mimo.app.network.ApiClient
import com.mimo.app.network.SyncPayload
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

class SyncWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        if (!TokenManager.isStudent(applicationContext)) return@withContext Result.success()
        val token = TokenManager.getToken(applicationContext) ?: return@withContext Result.success()
        val server = ApiClient.baseUrl
        val api = ApiClient.api
        val authorization = "Bearer $token"
        fun sameSession(): Boolean =
            TokenManager.getToken(applicationContext) == token && ApiClient.baseUrl == server

        try {
            val db = MimoDatabase.getDatabase(applicationContext, token, server)
            val statsDao = db.dailyStatsDao()

            for (usage in statsDao.pendingUsage()) {
                if (!sameSession()) return@withContext Result.success()
                api.pushSync(
                    SyncPayload(
                        date = usage.date,
                        mobileProductiveMin = if (usage.category == "productive") 1 else 0,
                        mobileDistractingMin = if (usage.category == "distracting") 1 else 0,
                        mobileNeutralMin = if (usage.category == "neutral") 1 else 0,
                        sync_id = usage.id,
                        app_name = usage.appName,
                    ),
                    authorization,
                )
                statsDao.removeUsage(usage.id)
            }

            val assignmentDao = db.assignmentDao()
            for (pending in assignmentDao.getUnsynced()) {
                if (!sameSession()) return@withContext Result.success()
                uploadAssignment(assignmentDao, api, pending)
            }

            if (!sameSession()) return@withContext Result.success()
            val pullData = api.pullSync(authorization)
            pullData.mergedStats?.let { statsDao.insertOrUpdate(it.toEntity(isSynced = true)) }
            db.assignmentDao().insertAll(pullData.assignments.map { it.toEntity(isSynced = true) })
            Result.success()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (error: HttpException) {
            if (error.code() in listOf(401, 403)) Result.success() else Result.retry()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
