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
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import com.mimo.app.MimoApplication
import com.mimo.app.data.DailyStatsEntity
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.ApiClient
import com.mimo.app.network.MockWindowEvent
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class MobileTrackerService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val CHANNEL_ID_FG = "mimo_tracker_fg_service"
    private var lastForegroundApp: String? = null
    private var distractingMinutes = 0
    private var lastRoastTime = 0L
    private val ROAST_COOLDOWN_MS = 5 * 60 * 1000L // 5 minutes

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

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1002, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(1002, notification)
        }

        if (!hasUsageStatsPermission()) {
            requestUsageStatsPermission()
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

    private fun requestUsageStatsPermission() {
        Log.w("MobileTracker", "PACKAGE_USAGE_STATS permission not granted. Launching Settings...")
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        try {
            startActivity(intent)
        } catch (e: Exception) {
            Log.e("MobileTracker", "Could not open Usage Access Settings", e)
        }
    }

    private fun startTracking() {
        serviceScope.launch {
            val usageStatsManager = getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
            if (usageStatsManager == null) {
                Log.w("MobileTracker", "UsageStatsManager service unavailable")
                return@launch
            }
            val db = MimoDatabase.getDatabase(applicationContext).dailyStatsDao()

            while (isActive) {
                if (!hasUsageStatsPermission()) {
                    Log.w("MobileTracker", "Waiting for PACKAGE_USAGE_STATS permission...")
                    delay(30_000)
                    continue
                }

                try {
                    val endTime = System.currentTimeMillis()
                    val startTime = endTime - 1000 * 60 // last minute

                    val events = usageStatsManager.queryEvents(startTime, endTime)
                    if (events != null) {
                        val event = UsageEvents.Event()
                        var currentForegroundApp: String? = null

                        while (events.hasNextEvent()) {
                            events.getNextEvent(event)
                            if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                                currentForegroundApp = event.packageName
                            }
                        }

                        if (currentForegroundApp != null) {
                            val category = categorizeApp(currentForegroundApp)
                            Log.d("MobileTracker", "Foreground App: $currentForegroundApp ($category)")

                            // Sync data to /screen/mock endpoint
                            try {
                                ApiClient.api.syncMockScreen(
                                    MockWindowEvent(
                                        app = currentForegroundApp,
                                        title = currentForegroundApp.substringAfterLast("."),
                                        category = category
                                    )
                                )
                                Log.d("MobileTracker", "Synced $currentForegroundApp to /screen/mock")
                            } catch (e: Exception) {
                                Log.e("MobileTracker", "Failed to sync to /screen/mock: ${e.message}")
                            }

                            if (category == "distracting") {
                                distractingMinutes++
                                if (distractingMinutes >= 2 && (System.currentTimeMillis() - lastRoastTime) > ROAST_COOLDOWN_MS) {
                                    fireLocalRoast(currentForegroundApp)
                                    lastRoastTime = System.currentTimeMillis()
                                    distractingMinutes = 0 // reset after roasting
                                }
                            } else {
                                distractingMinutes = 0 // reset if they switch to something else
                            }

                            // Update local stats every minute
                            val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                            val currentStats = db.getByDate(today)
                            
                            val prodDelta = if (category == "productive") 1 else 0
                            val distDelta = if (category == "distracting") 1 else 0
                            val neutDelta = if (category == "neutral") 1 else 0
                            
                            if (prodDelta > 0 || distDelta > 0 || neutDelta > 0) {
                                val prod = (currentStats?.productiveMin ?: 0) + prodDelta
                                val dist = (currentStats?.distractingMin ?: 0) + distDelta
                                val neut = (currentStats?.neutralMin ?: 0) + neutDelta
                                val total = prod + dist + neut
                                val score = if (total > 0) (prod.toDouble() / (prod + dist).coerceAtLeast(1)) * 100.0 else 0.0

                                val updatedEntity = DailyStatsEntity(
                                    date = today,
                                    productiveMin = prod,
                                    distractingMin = dist,
                                    neutralMin = neut,
                                    focusScore = score,
                                    isSynced = false
                                )
                                db.insertOrUpdate(updatedEntity)
                            }
                        }
                    }
                } catch (e: SecurityException) {
                    Log.e("MobileTracker", "SecurityException during usage stats query: ${e.message}")
                    requestUsageStatsPermission()
                } catch (e: Exception) {
                    Log.e("MobileTracker", "Exception during usage stats query: ${e.message}")
                }

                delay(60_000) // Check once a minute
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

    private fun fireLocalRoast(packageName: String) {
        val appName = packageName.substringAfterLast(".")
        val message = "Really? You're spending your time on $appName on your phone? Put it down and get back to work!"
        
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notification = NotificationCompat.Builder(this, MimoApplication.CHANNEL_ID_ROASTS)
            .setContentTitle("Mimo Local Roast \uD83D\uDD25")
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .build()

        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
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
