package com.mimo.app.ui

import android.app.Activity
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.mimo.app.data.TokenManager
import com.mimo.app.network.ApiClient
import com.mimo.app.network.LoginRequest
import com.mimo.app.network.RegisterRequest
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(onLoginSuccess: (Boolean) -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var isRegisterMode by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }

    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Mimo",
            style = MaterialTheme.typography.displayMedium,
            color = MaterialTheme.colorScheme.primary
        )
        Text(
            text = if (isRegisterMode) "Create an Account" else "Welcome Back",
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
        )

        // Tab Selector for Login vs Register
        TabRow(
            selectedTabIndex = if (isRegisterMode) 1 else 0,
            modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)
        ) {
            Tab(
                selected = !isRegisterMode,
                onClick = {
                    isRegisterMode = false
                    errorMessage = null
                },
                text = { Text("Login") }
            )
            Tab(
                selected = isRegisterMode,
                onClick = {
                    isRegisterMode = true
                    errorMessage = null
                },
                text = { Text("Register") }
            )
        }

        if (isRegisterMode) {
            OutlinedTextField(
                value = displayName,
                onValueChange = { displayName = it },
                label = { Text("Display Name") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
        }

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email Address") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Next
            )
        )

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Password,
                imeAction = ImeAction.Done
            )
        )

        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.padding(16.dp))
        } else {
            Button(
                onClick = {
                    if (email.isBlank() || password.isBlank()) {
                        errorMessage = "Please enter email and password"
                        return@Button
                    }
                    if (isRegisterMode && password.length < 8) {
                        errorMessage = "Password must be at least 8 characters"
                        return@Button
                    }

                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null
                        try {
                            val authResponse = if (isRegisterMode) {
                                ApiClient.api.register(
                                    RegisterRequest(
                                        email = email.trim(),
                                        password = password,
                                        role = "student",
                                        display_name = displayName.ifBlank { null }
                                    )
                                )
                            } else {
                                ApiClient.api.login(
                                    LoginRequest(
                                        email = email.trim(),
                                        password = password
                                    )
                                )
                            }

                            TokenManager.saveToken(context, authResponse.access_token)
                            TokenManager.setOnboardingCompleted(context, authResponse.user.onboarding_completed)
                            onLoginSuccess(authResponse.user.onboarding_completed)
                        } catch (e: Exception) {
                            Log.e("LoginScreen", "Auth error", e)
                            errorMessage = e.localizedMessage ?: "Authentication failed. Check credentials."
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(50.dp)
            ) {
                Text(if (isRegisterMode) "Register" else "Login")
            }

            Spacer(modifier = Modifier.height(16.dp))
            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Optional Google Sign-In
            OutlinedButton(
                onClick = {
                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null
                        val credentialManager = CredentialManager.create(context)
                        val googleIdOption = GetGoogleIdOption.Builder()
                            .setFilterByAuthorizedAccounts(false)
                            .setServerClientId("YOUR_WEB_CLIENT_ID")
                            .setAutoSelectEnabled(true)
                            .build()

                        val request = GetCredentialRequest.Builder()
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
                                val res = ApiClient.api.authenticateGoogle(mapOf("token" to idToken))
                                val token = res["access_token"] as? String
                                val userMap = res["user"] as? Map<*, *>
                                val onboardingCompleted = userMap?.get("onboarding_completed") as? Boolean ?: false
                                if (!token.isNullOrBlank()) {
                                    TokenManager.saveToken(context, token)
                                    TokenManager.setOnboardingCompleted(context, onboardingCompleted)
                                }
                                onLoginSuccess(onboardingCompleted)
                            } else {
                                errorMessage = "Unexpected credential type"
                            }
                        } catch (e: GetCredentialException) {
                            errorMessage = "Google sign-in failed: ${e.message}"
                        } catch (e: Exception) {
                            errorMessage = "Backend auth failed: ${e.message}"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(50.dp)
            ) {
                Text("Sign in with Google")
            }
        }

        errorMessage?.let {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = it,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}
