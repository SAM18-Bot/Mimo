package com.mimo.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.mimo.app.data.TokenManager
import com.mimo.app.tracker.DeviceTracking
import com.mimo.app.ui.*
import com.mimo.app.ui.theme.MimoTheme

enum class AppScreen { Login, Onboarding, Permissions, Dashboard, Parent }

class MainActivity : ComponentActivity() {
    private fun screen(): AppScreen = when (TokenManager.role(this)) {
        "parent" -> AppScreen.Parent
        "student" -> when {
            !TokenManager.isOnboardingCompleted(this) -> AppScreen.Onboarding
            !DeviceTracking.prefs(this).getBoolean("permissions_seen", false) -> AppScreen.Permissions
            else -> AppScreen.Dashboard
        }
        else -> AppScreen.Login
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        TokenManager.init(this)
        setContent {
            val theme by Appearance.theme.collectAsState()
            MimoTheme(darkTheme = theme == ThemeChoice.Dark || (theme == ThemeChoice.System && isSystemInDarkTheme())) {
                var current by remember { mutableStateOf(screen()) }
                val expired by TokenManager.sessionExpired.collectAsState()
                LaunchedEffect(expired) {
                    if (expired) {
                        viewModelStore.clear()
                        current = AppScreen.Login
                    }
                }
                Surface(modifier = Modifier.fillMaxSize()) {
                    when (if (expired) AppScreen.Login else current) {
                        AppScreen.Login -> LoginScreen { current = screen() }
                        AppScreen.Parent -> ParentScreen()
                        AppScreen.Onboarding -> OnboardingScreen {
                            TokenManager.setOnboardingCompleted(this, true)
                            current = screen()
                        }
                        AppScreen.Permissions -> PermissionsScreen {
                            DeviceTracking.prefs(this).edit().putBoolean("permissions_seen", true).apply()
                            current = AppScreen.Dashboard
                        }
                        AppScreen.Dashboard -> {
                            LaunchedEffect(Unit) { DeviceTracking.apply(this@MainActivity) }
                            MainScreen()
                        }
                    }
                }
            }
        }
    }
}
