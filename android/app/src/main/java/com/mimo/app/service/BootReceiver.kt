package com.mimo.app.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.mimo.app.data.TokenManager
import com.mimo.app.tracker.DeviceTracking

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action !in setOf(Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED)) return
        if (TokenManager.isStudent(context) && DeviceTracking.prefs(context).getBoolean("autostart", true)) {
            DeviceTracking.apply(context)
        }
    }
}
