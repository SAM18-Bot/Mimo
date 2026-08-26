package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mimo.app.ui.DashboardViewModel
import com.mimo.app.ui.components.FocusScoreGauge
import com.mimo.app.ui.components.ScreenTimeBar
import com.mimo.app.ui.components.StatsRow

@Composable
fun HomeScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier) {
    val stats by viewModel.stats.collectAsState()
    val screenBreakdown by viewModel.screenBreakdown.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        FocusScoreGauge(
            score = stats.focus_score,
            letterGrade = stats.letter_grade
        )

        StatsRow(stats = stats)

        ScreenTimeBar(breakdown = screenBreakdown)

        // Pomodoro Timer
        PomodoroTimer()
    }
}

@Composable
fun PomodoroTimer() {
    var timeLeft by remember { mutableStateOf(25 * 60) }
    var isRunning by remember { mutableStateOf(false) }

    LaunchedEffect(isRunning) {
        while (isRunning && timeLeft > 0) {
            kotlinx.coroutines.delay(1000)
            timeLeft--
        }
        if (timeLeft == 0) isRunning = false
    }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Focus Session Timer", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(16.dp))
            val minutes = timeLeft / 60
            val seconds = timeLeft % 60
            Text(
                text = String.format("%02d:%02d", minutes, seconds),
                style = MaterialTheme.typography.displayLarge
            )
            Spacer(modifier = Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { isRunning = !isRunning }) {
                    Text(if (isRunning) "Pause" else "Start")
                }
                OutlinedButton(onClick = {
                    isRunning = false
                    timeLeft = 25 * 60
                }) {
                    Text("Reset")
                }
            }
        }
    }
}
