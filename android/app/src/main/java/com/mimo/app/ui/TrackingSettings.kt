package com.mimo.app.ui

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.mimo.app.tracker.DeviceTracking

@Composable
fun TrackingSettings() {
    val context = LocalContext.current
    val prefs = remember { DeviceTracking.prefs(context) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var allowed by remember { mutableStateOf(hasUsageStatsPermission(context)) }
    var enabled by remember { mutableStateOf(prefs.getBoolean("enabled", true)) }
    var boot by remember { mutableStateOf(prefs.getBoolean("autostart", true)) }
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                allowed = hasUsageStatsPermission(context)
                DeviceTracking.apply(context)
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Track usage on this device", Modifier.weight(1f))
            Switch(enabled, onCheckedChange = {
                enabled = it
                prefs.edit().putBoolean("enabled", it).apply()
                DeviceTracking.apply(context)
            })
        }
        if (!allowed) TextButton(onClick = {
            context.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
        }) { Text("Grant usage access") }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Resume services after restart", Modifier.weight(1f))
            Switch(boot, onCheckedChange = { boot = it; prefs.edit().putBoolean("autostart", it).apply() })
        }
    }
}
