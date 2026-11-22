package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mimo.app.data.TokenManager
import com.mimo.app.ui.DashboardViewModel
import com.mimo.app.network.ApiClient
import android.content.Intent
import com.mimo.app.MainActivity
import com.mimo.app.MimoApplication
import com.mimo.app.service.RoastEnforcementService
import com.mimo.app.tracker.MobileTrackerService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

@Suppress("UNUSED_PARAMETER")
@Composable
fun SettingsScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var inviteCode by remember { mutableStateOf<String?>(null) }
    var inviteError by remember { mutableStateOf<String?>(null) }
    var isGeneratingInvite by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .fillMaxSize().verticalScroll(rememberScrollState())
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        Text("Settings", style = MaterialTheme.typography.headlineMedium)

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("Parent Portal", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text("Generate a one-time code for a parent to link this account.")
                Button(
                    onClick = {
                        coroutineScope.launch {
                            isGeneratingInvite = true
                            inviteError = null
                            try {
                                inviteCode = ApiClient.api.createParentInvite().code
                            } catch (e: Exception) {
                                inviteError = e.localizedMessage ?: "Could not generate an invite code"
                            } finally {
                                isGeneratingInvite = false
                            }
                        }
                    },
                    enabled = !isGeneratingInvite,
                ) {
                    if (isGeneratingInvite) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                    } else {
                        Text("Generate Invite Code")
                    }
                }
                inviteCode?.let { Text("Invite Code: $it", color = MaterialTheme.colorScheme.primary) }
                inviteError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        }

        com.mimo.app.ui.TrackingSettings()
        com.mimo.app.ui.AppearanceSetting()
        com.mimo.app.ui.GeminiKeySetting()
        com.mimo.app.ui.ServerSetting()
        com.mimo.app.ui.SignOutButton()
    }
}
