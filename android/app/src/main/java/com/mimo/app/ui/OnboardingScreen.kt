package com.mimo.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.mimo.app.network.ApiClient
import com.mimo.app.network.OnboardingRequest
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(onOnboardingFinished: () -> Unit) {
    val coroutineScope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    var courseMajor by remember { mutableStateOf("") }
    var age by remember { mutableStateOf("") }
    var educationLevel by remember { mutableStateOf("undergraduate") }
    var aiEngine by remember { mutableStateOf("gemini") }
    var wakeTime by remember { mutableStateOf("07:00") }
    var sleepTime by remember { mutableStateOf("23:00") }
    var dailyStudyGoal by remember { mutableStateOf("120") }
    
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    val eduLevels = listOf("high_school", "undergraduate", "graduate")
    val engines = listOf("gemini", "openai")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(scrollState),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Welcome to Mimo",
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(top = 24.dp)
        )
        Text(text = "Let's personalize your experience.")

        OutlinedTextField(
            value = courseMajor,
            onValueChange = { courseMajor = it },
            label = { Text("Course / Major") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = age,
            onValueChange = { age = it },
            label = { Text("Age") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth()
        )

        // Education Level Dropdown
        var eduExpanded by remember { mutableStateOf(false) }
        ExposedDropdownMenuBox(
            expanded = eduExpanded,
            onExpandedChange = { eduExpanded = !eduExpanded },
            modifier = Modifier.fillMaxWidth()
        ) {
            OutlinedTextField(
                value = educationLevel,
                onValueChange = {},
                readOnly = true,
                label = { Text("Education Level") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = eduExpanded) },
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(
                expanded = eduExpanded,
                onDismissRequest = { eduExpanded = false }
            ) {
                eduLevels.forEach { level ->
                    DropdownMenuItem(
                        text = { Text(level) },
                        onClick = {
                            educationLevel = level
                            eduExpanded = false
                        }
                    )
                }
            }
        }

        // AI Engine Dropdown
        var engineExpanded by remember { mutableStateOf(false) }
        ExposedDropdownMenuBox(
            expanded = engineExpanded,
            onExpandedChange = { engineExpanded = !engineExpanded },
            modifier = Modifier.fillMaxWidth()
        ) {
            OutlinedTextField(
                value = aiEngine,
                onValueChange = {},
                readOnly = true,
                label = { Text("AI Engine") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = engineExpanded) },
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(
                expanded = engineExpanded,
                onDismissRequest = { engineExpanded = false }
            ) {
                engines.forEach { engine ->
                    DropdownMenuItem(
                        text = { Text(engine) },
                        onClick = {
                            aiEngine = engine
                            engineExpanded = false
                        }
                    )
                }
            }
        }

        OutlinedTextField(
            value = wakeTime,
            onValueChange = { wakeTime = it },
            label = { Text("Wake Time (HH:MM)") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = sleepTime,
            onValueChange = { sleepTime = it },
            label = { Text("Sleep Time (HH:MM)") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = dailyStudyGoal,
            onValueChange = { dailyStudyGoal = it },
            label = { Text("Daily Study Goal (minutes)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth()
        )

        errorMessage?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = {
                if (courseMajor.isBlank() || age.isBlank()) {
                    errorMessage = "Please fill in all fields"
                    return@Button
                }
                coroutineScope.launch {
                    isLoading = true
                    try {
                        ApiClient.api.completeOnboarding(
                            OnboardingRequest(
                                course_major = courseMajor,
                                age = age.toIntOrNull() ?: 18,
                                education_level = educationLevel,
                                ai_engine = aiEngine,
                                wake_time = wakeTime,
                                sleep_time = sleepTime,
                                daily_study_goal_min = dailyStudyGoal.toIntOrNull() ?: 120
                            )
                        )
                        onOnboardingFinished()
                    } catch (e: Exception) {
                        errorMessage = "Failed to complete onboarding: ${e.message}"
                    } finally {
                        isLoading = false
                    }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
                .padding(bottom = 16.dp),
            enabled = !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
            } else {
                Text("Complete Onboarding")
            }
        }
    }
}
