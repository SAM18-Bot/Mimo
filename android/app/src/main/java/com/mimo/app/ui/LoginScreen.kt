package com.mimo.app.ui

import android.app.Activity
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.mimo.app.network.ApiClient
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Welcome to Mimo", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(32.dp))

        if (isLoading) {
            Text("Signing in...")
        } else {
            Button(onClick = {
                coroutineScope.launch {
                    isLoading = true
                    errorMessage = null
                    val credentialManager = CredentialManager.create(context)
                    
                    val googleIdOption: GetGoogleIdOption = GetGoogleIdOption.Builder()
                        .setFilterByAuthorizedAccounts(false)
                        .setServerClientId("YOUR_WEB_CLIENT_ID") // Replace with actual Client ID
                        .setAutoSelectEnabled(true)
                        .build()

                    val request: GetCredentialRequest = GetCredentialRequest.Builder()
                        .addCredentialOption(googleIdOption)
                        .build()

                    try {
                        val result = credentialManager.getCredential(
                            request = request,
                            context = context as Activity
                        )
                        
                        val credential = result.credential
                        if (credential is GoogleIdTokenCredential) {
                            val idToken = credential.idToken
                            Log.d("LoginScreen", "Got ID token")
                            
                            // Send token to backend
                            try {
                                ApiClient.api.authenticateGoogle(mapOf("token" to idToken))
                                onLoginSuccess()
                            } catch (e: Exception) {
                                errorMessage = "Backend auth failed: ${e.message}"
                            }
                        } else {
                            errorMessage = "Unexpected credential type"
                        }
                    } catch (e: GetCredentialException) {
                        errorMessage = "Sign-in failed: ${e.message}"
                    } finally {
                        isLoading = false
                    }
                }
            }) {
                Text("Sign in with Google")
            }
        }

        errorMessage?.let {
            Spacer(modifier = Modifier.height(16.dp))
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}
