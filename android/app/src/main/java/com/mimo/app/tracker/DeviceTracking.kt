package com.mimo.app.tracker

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import com.mimo.app.data.MimoDatabase
import com.mimo.app.data.TokenManager
import com.mimo.app.network.ApiClient
import com.mimo.app.service.RoastEnforcementService
import com.mimo.app.ui.hasUsageStatsPermission

object DeviceTracking {
    fun prefs(context: Context) = context.getSharedPreferences(
        "tracking_" + MimoDatabase.accountNamespace(TokenManager.getToken(context), ApiClient.baseUrl),
        Context.MODE_PRIVATE
    )

    fun enabled(context: Context) = TokenManager.isStudent(context) && prefs(context).getBoolean("enabled", true)
    fun alertsAllowed(context: Context) = Build.VERSION.SDK_INT < 33 ||
        ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    fun apply(context: Context) {
        val tracker = Intent(context, MobileTrackerService::class.java)
        val alerts = Intent(context, RoastEnforcementService::class.java)
        val student = TokenManager.isStudent(context)
        if (student && alertsAllowed(context)) {
            runCatching { ContextCompat.startForegroundService(context, alerts) }
        } else context.stopService(alerts)
        if (enabled(context) && hasUsageStatsPermission(context)) {
            runCatching { ContextCompat.startForegroundService(context, tracker) }
        } else context.stopService(tracker)
    }
}
