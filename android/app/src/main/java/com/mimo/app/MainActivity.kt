package com.mimo.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import com.mimo.app.data.TokenManager
import com.mimo.app.service.RoastEnforcementService
import com.mimo.app.tracker.MobileTrackerService
import com.mimo.app.ui.DashboardScreen
import com.mimo.app.ui.LoginScreen

class MainActivity : ComponentActivity() {

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startServices()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        TokenManager.init(this)

        // Request notification permission on Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this, Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                startServices()
            } else {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        } else {
            startServices()
        }

        setContent {
            var isLoggedIn by remember { mutableStateOf(TokenManager.isLoggedIn(this@MainActivity)) }

            if (isLoggedIn) {
                DashboardScreen()
            } else {
                LoginScreen(
                    onLoginSuccess = {
                        isLoggedIn = true
                    }
                )
            }
        }
    }

    private fun startServices() {
        val roastIntent = Intent(this, RoastEnforcementService::class.java)
        val trackerIntent = Intent(this, MobileTrackerService::class.java)
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(roastIntent)
            } else {
                startService(roastIntent)
            }
        }
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(trackerIntent)
            } else {
                startService(trackerIntent)
            }
        }
    }
}
