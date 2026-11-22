package com.mimo.app.ui

import android.content.Context
import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.input.PasswordVisualTransformation
import com.mimo.app.network.AccountApi
import com.mimo.app.network.PersonalKeyRequest
import com.mimo.app.MainActivity
import com.mimo.app.MimoApplication
import com.mimo.app.data.TokenManager
import com.mimo.app.network.ApiClient
import com.mimo.app.service.RoastEnforcementService
import com.mimo.app.tracker.MobileTrackerService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class ThemeChoice { System, Light, Dark }

object Appearance {
    private val current = MutableStateFlow(ThemeChoice.System)
    val theme = current.asStateFlow()

    fun restore(context: Context) {
        val stored = context.getSharedPreferences("mimo_display", Context.MODE_PRIVATE).getString("theme", null)
        current.value = ThemeChoice.values().firstOrNull { it.name == stored } ?: ThemeChoice.System
    }

    fun set(context: Context, theme: ThemeChoice) {
        context.getSharedPreferences("mimo_display", Context.MODE_PRIVATE).edit().putString("theme", theme.name).apply()
        current.value = theme
    }
}

@Composable
fun AppearanceSetting() {
    val context = LocalContext.current
    val current by Appearance.theme.collectAsState()
    Column {
        Text("Appearance", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ThemeChoice.values().forEach { choice ->
                FilterChip(selected = current == choice, onClick = { Appearance.set(context, choice) },
                    label = { Text(choice.name) })
            }
        }
    }
}

@Composable
fun GeminiKeySetting() {
    val account = remember { ApiClient.createService(AccountApi::class.java) }
    val scope = rememberCoroutineScope()
    var key by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    fun save(value: String) {
        busy = true
        scope.launch {
            try {
                account.updatePersonalKey(PersonalKeyRequest(value))
                key = ""
                status = if (value.isEmpty()) "Using the server key." else "Personal key saved."
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                status = "Could not update your key."
            } finally {
                busy = false
            }
        }
    }
    Column {
        OutlinedTextField(key, { key = it.take(100) }, label = { Text("Personal Gemini API key") },
            singleLine = true, visualTransformation = PasswordVisualTransformation(), enabled = !busy)
        Row {
            TextButton(enabled = !busy && key.isNotBlank(), onClick = { save(key.trim()) }) { Text("Save key") }
            TextButton(enabled = !busy, onClick = { save("") }) { Text("Use server key") }
        }
        if (status.isNotEmpty()) Text(status)
    }
}

@Composable
fun ServerSetting(enabled: Boolean = true, onChanged: () -> Unit = {}) {
    val context = LocalContext.current
    var open by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    TextButton(enabled = enabled, onClick = {
        draft = ApiClient.baseUrl
        error = null
        open = true
    }) { Text("Change server") }
    if (open) {
        AlertDialog(
            onDismissRequest = { open = false },
            title = { Text("Mimo server") },
            text = {
                Column {
                    if (TokenManager.isLoggedIn(context)) Text("Changing servers signs you out on this device.")
                    OutlinedTextField(draft, { draft = it; error = null }, label = { Text("HTTPS server address") },
                        singleLine = true, isError = error != null)
                    error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val normalized = try {
                        ApiClient.normalizeOrigin(draft)
                    } catch (_: IllegalArgumentException) {
                        error = "Enter an HTTPS address with no path, credentials, query, or fragment."
                        return@TextButton
                    }
                    open = false
                    if (normalized != ApiClient.baseUrl) {
                        val signedIn = TokenManager.isLoggedIn(context)
                        if (signedIn) endSession(context)
                        ApiClient.updateBaseUrl(normalized)
                        if (signedIn) returnToSignIn(context) else onChanged()
                    }
                }) { Text("Use server") }
            },
            dismissButton = { TextButton(onClick = { open = false }) { Text("Cancel") } }
        )
    }
}

private fun endSession(context: Context) {
    val token = TokenManager.getToken(context)
    val api = ApiClient.api
    TokenManager.clearToken(context)
    context.stopService(Intent(context, RoastEnforcementService::class.java))
    context.stopService(Intent(context, MobileTrackerService::class.java))
    if (token != null) MimoApplication.instance.applicationScope.launch {
        try {
            api.logout("Bearer $token")
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            // Offline sign-out already removed the credential from this device.
        }
    }
}

private fun returnToSignIn(context: Context) {
    context.startActivity(Intent(context, MainActivity::class.java).apply {
        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
    })
}

@Composable
fun SignOutButton() {
    val context = LocalContext.current
    OutlinedButton(onClick = {
        endSession(context)
        returnToSignIn(context)
    }) { Text("Sign out") }
}
