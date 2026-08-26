package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
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
import android.content.Intent
import com.mimo.app.MainActivity

@Composable
fun SettingsScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var isParentPortalEnabled by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        Text("Settings", style = MaterialTheme.typography.headlineMedium)

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("Parent Portal", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Enable Parent Portal")
                    Switch(checked = isParentPortalEnabled, onCheckedChange = { isParentPortalEnabled = it })
                }
                if (isParentPortalEnabled) {
                    Text("Invite Code: ABC-123 (Mock)", color = MaterialTheme.colorScheme.primary)
                }
            }
        }

        Button(
            onClick = {
                TokenManager.clearToken(context)
                val intent = Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
                context.startActivity(intent)
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
        ) {
            Text("Sign Out")
        }
    }
}
