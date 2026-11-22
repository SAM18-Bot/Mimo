package com.mimo.app.tracker

import android.app.AppOpsManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.mimo.app.MimoApplication
import com.mimo.app.data.PendingUsage
import com.mimo.app.data.TokenManager
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.ApiClient
import com.mimo.app.network.MockWindowEvent
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class MobileTrackerService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val CHANNEL_ID_FG = "mimo_tracker_fg_service"

    // Categorization
    private val distractingApps = setOf(
        "com.instagram.android",
        "com.zhiliaoapp.musically", // TikTok
        "com.twitter.android",
        "com.google.android.youtube",
        "com.facebook.katana",
        "com.snapchat.android",
        "com.reddit.frontpage"
    )

    private val productiveApps = setOf(
        "com.google.android.apps.docs",
        "com.microsoft.office.word",
        "com.slack",
        "com.github.android"
    )

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID_FG)
            .setContentTitle("Mimo Tracker")
            .setContentText("Monitoring mobile usage...")
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(1002, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(1002, notification)
        }

        if (!DeviceTracking.enabled(this) || !hasUsageStatsPermission()) {
            Log.w("MobileTracker", "PACKAGE_USAGE_STATS permission not granted. Waiting for UI flow.")
        }

        if (!TokenManager.isLoggedIn(this)) {
            stopSelf()
            return START_NOT_STICKY
        }
        startTracking()
        return START_STICKY
    }

    private fun hasUsageStatsPermission(): Boolean {
        val appOps = getSystemService(Context.APP_OPS_SERVICE) as? AppOpsManager ?: return false
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                packageName
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                packageName
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    // Removed requestUsageStatsPermission() since background startActivity is blocked in Android 10+

    private var trackingJob: kotlinx.coroutines.Job? = null

    private fun startTracking() {
        if (trackingJob?.isActive == true) return
        val token = TokenManager.getToken(this) ?: return
        val server = ApiClient.baseUrl
        trackingJob = serviceScope.launch {
            val usageStatsManager = getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
            if (usageStatsManager == null) {
                Log.w("MobileTracker", "UsageStatsManager service unavailable")
                return@launch
            }
            val db = MimoDatabase.getDatabase(applicationContext, token, server).dailyStatsDao()
            val api = ApiClient.api
            val power = getSystemService(android.os.PowerManager::class.java)
            var warnedThisStreak = false
            var currentForegroundApp: String? = null
            var lastSample = System.currentTimeMillis() - 60_000L

            while (isActive && TokenManager.getToken(this@MobileTrackerService) == token && ApiClient.baseUrl == server) {
                if (!hasUsageStatsPermission()) {
                    Log.w("MobileTracker", "Waiting for PACKAGE_USAGE_STATS permission...")
                    delay(30_000)
                    continue
                }

                try {
                    val endTime = System.currentTimeMillis()
                    if (endTime < lastSample) {
                        currentForegroundApp = null
                        lastSample = endTime - 60_000L
                    }
                    val events = usageStatsManager.queryEvents(lastSample, endTime)
                    lastSample = endTime
                    if (events != null) {
                        val event = UsageEvents.Event()
                        while (events.hasNextEvent()) {
                            events.getNextEvent(event)
                            when (event.eventType) {
                                UsageEvents.Event.ACTIVITY_RESUMED -> currentForegroundApp = event.packageName
                                UsageEvents.Event.ACTIVITY_PAUSED, UsageEvents.Event.ACTIVITY_STOPPED -> {
                                    if (currentForegroundApp == event.packageName) currentForegroundApp = null
                                }
                            }
                        }

                        val app = currentForegroundApp
                        if (app == null || power?.isInteractive != true) warnedThisStreak = false
                        if (app != null && power?.isInteractive == true) {
                            if (TokenManager.getToken(this@MobileTrackerService) != token ||
                                ApiClient.baseUrl != server
                            ) return@launch
                            val category = categorizeApp(app)
                            val today = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date())
                            val label = try {
                                packageManager.getApplicationLabel(packageManager.getApplicationInfo(app, 0)).toString()
                            } catch (_: android.content.pm.PackageManager.NameNotFoundException) { app }
                            db.enqueueUsage(PendingUsage(UUID.randomUUID().toString(), today, category, label.take(200)))

                            // Send the live activity event separately from the durable usage batch.
                            try {
                                val live = api.syncMockScreen(
                                    MockWindowEvent(
                                        app = app,
                                        title = app.substringAfterLast("."),
                                        category = category
                                    ),
                                    authorization = "Bearer $token",
                                )
                                val warn = category == "distracting" && live["study_block_active"] == true
                                if (warn && !warnedThisStreak && DeviceTracking.alertsAllowed(this@MobileTrackerService)
                                    && TokenManager.getToken(this@MobileTrackerService) == token) {
                                    val notice = NotificationCompat.Builder(this@MobileTrackerService, MimoApplication.CHANNEL_ID_ROASTS)
                                        .setContentTitle("Scheduled study time").setContentText("Return to your study block when you're ready.")
                                        .setSmallIcon(android.R.drawable.ic_dialog_info).setAutoCancel(true).build()
                                    getSystemService(NotificationManager::class.java).notify(1003, notice)
                                }
                                warnedThisStreak = warn
                            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                                throw cancelled
                            } catch (_: Exception) {
                                Log.w("MobileTracker", "Could not send live activity")
                            }

                        }
                    }
                } catch (cancelled: kotlinx.coroutines.CancellationException) {
                    throw cancelled
                } catch (e: SecurityException) {
                    Log.w("MobileTracker", "Usage statistics permission is unavailable")
                } catch (e: Exception) {
                    Log.w("MobileTracker", "Could not record usage statistics")
                }

                delay(60_000)
            }
        }
    }

    private fun categorizeApp(packageName: String): String {
        return when {
            distractingApps.contains(packageName) -> "distracting"
            productiveApps.contains(packageName) -> "productive"
            else -> "neutral"
        }
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID_FG,
            "Mimo Mobile Tracker",
            NotificationManager.IMPORTANCE_LOW
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager?.createNotificationChannel(channel)
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}
