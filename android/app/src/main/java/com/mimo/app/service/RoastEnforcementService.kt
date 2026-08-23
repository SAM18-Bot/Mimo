package com.mimo.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.mimo.app.MimoApplication
import com.mimo.app.network.WebSocketManager
import com.mimo.app.data.TokenManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class RoastEnforcementService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val webSocketManager = WebSocketManager()
    private val CHANNEL_ID_FG = "mimo_fg_service"

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID_FG)
            .setContentTitle("Mimo")
            .setContentText("Mimo is watching...")
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1001, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(1001, notification)
        }

        webSocketManager.connect(TokenManager.getToken(this))

        serviceScope.launch {
            webSocketManager.events.collectLatest { event ->
                if (event.type == "roast" && event.message != null) {
                    showRoastNotification(event.message)
                }
                else if (event.type == "voice_response" && event.message != null) {
                    showCoachNotification(event.message)
                }
                else if (event.type == "reminder" && event.message != null) {
                    showReminderNotification(event.message)
                }
                else if (event.type == "todo_reminder" && event.message != null) {
                    showReminderNotification(event.message)
                }
            }
        }

        return START_STICKY
    }

    private fun showRoastNotification(message: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notification = NotificationCompat.Builder(this, MimoApplication.CHANNEL_ID_ROASTS)
            .setContentTitle("Mimo is watching \ud83d\udc40")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .build()
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun showReminderNotification(message: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val builder = NotificationCompat.Builder(this, MimoApplication.CHANNEL_ID_ROASTS)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Mimo Reminder")
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))

        notificationManager.notify(System.currentTimeMillis().toInt(), builder.build())
    }

    private fun showCoachNotification(message: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notification = NotificationCompat.Builder(this, MimoApplication.CHANNEL_ID_ROASTS)
            .setContentTitle("Coach \ud83e\uddd1\u200d\ud83c\udfeb")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .build()
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID_FG,
            "Mimo Background Service",
            NotificationManager.IMPORTANCE_LOW
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager?.createNotificationChannel(channel)
    }

    override fun onDestroy() {
        super.onDestroy()
        webSocketManager.disconnect()
        serviceScope.cancel()
    }
}
