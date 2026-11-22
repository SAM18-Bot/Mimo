package com.mimo.app.ui

import android.app.Activity
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.mimo.app.network.AccountApi
import com.mimo.app.network.GoogleLogin
import com.mimo.app.network.AuthResponse
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import kotlinx.coroutines.CancellationException
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

    var role by remember { mutableStateOf("student") }
    var origin by remember { mutableStateOf(ApiClient.baseUrl) }
    var clientId by remember(origin) { mutableStateOf("") }
    val account = remember(origin) { ApiClient.createService(AccountApi::class.java) }
    LaunchedEffect(origin) {
        try {
            clientId = account.googleClientId().client_id.orEmpty()
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            clientId = ""
        }
    }
    fun complete(response: AuthResponse) {
        TokenManager.saveToken(context, response.access_token)
        TokenManager.setOnboardingCompleted(context, response.user.onboarding_completed)
        onLoginSuccess(response.user.onboarding_completed)
    }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize().verticalScroll(rememberScrollState())
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
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("student", "parent").forEach { value ->
                    FilterChip(selected = value == role, onClick = { role = value },
                        label = { Text(value.replaceFirstChar(Char::uppercase)) })
                }
            }
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
                                        role = role,
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

                            complete(authResponse)
                        } catch (e: CancellationException) {
                            throw e
                        } catch (e: Exception) {
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
            
        }

        if (!isRegisterMode && clientId.isNotBlank()) {
            OutlinedButton(enabled = !isLoading, onClick = {
                coroutineScope.launch {
                    isLoading = true
                    errorMessage = null
                    try {
                        val option = GetSignInWithGoogleOption.Builder(clientId).build()
                        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
                        val credential = CredentialManager.create(context).getCredential(context, request).credential
                        val googleToken = GoogleIdTokenCredential.createFrom(credential.data).idToken
                        complete(account.googleLogin(GoogleLogin(googleToken)))
                    } catch (_: GetCredentialCancellationException) {
                        // The chooser was dismissed.
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        errorMessage = "Google sign-in could not be completed. Try again or use email."
                    } finally { isLoading = false }
                }
            }) { Text("Sign in with Google") }
        }
        ServerSetting(enabled = !isLoading, onChanged = { origin = ApiClient.baseUrl })
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
