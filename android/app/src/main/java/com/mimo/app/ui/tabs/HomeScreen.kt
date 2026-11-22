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
    val cached by viewModel.stats.collectAsState()
    val live by viewModel.liveStats.collectAsState()
    val stats = live?.takeIf { it.date == cached.date } ?: cached
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

        LiveActivity(viewModel, screenBreakdown, stats)

        // Pomodoro Timer
        PomodoroTimer()
    }
}

@Composable
fun PomodoroTimer() {
    var minutes by androidx.compose.runtime.saveable.rememberSaveable { mutableIntStateOf(25) }
    var remaining by androidx.compose.runtime.saveable.rememberSaveable { mutableIntStateOf(minutes * 60) }
    var deadline by androidx.compose.runtime.saveable.rememberSaveable { mutableLongStateOf(0L) }
    LaunchedEffect(deadline) {
        while (deadline != 0L) {
            remaining = ((deadline - android.os.SystemClock.elapsedRealtime() + 999) / 1000).toInt().coerceAtLeast(0)
            if (remaining == 0) deadline = 0L else kotlinx.coroutines.delay(250)
        }
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Focus timer", style = MaterialTheme.typography.titleMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(25, 50).forEach { value -> FilterChip(value == minutes, {
                    deadline = 0L; minutes = value; remaining = value * 60
                }, label = { Text("${value}m") }) }
            }
            Text("%02d:%02d".format(remaining / 60, remaining % 60), style = MaterialTheme.typography.displayLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    if (deadline == 0L) {
                        if (remaining == 0) remaining = minutes * 60
                        deadline = android.os.SystemClock.elapsedRealtime() + remaining * 1000L
                    } else deadline = 0L
                }) { Text(if (deadline == 0L) "Start" else "Pause") }
                OutlinedButton(onClick = { deadline = 0L; remaining = minutes * 60 }) { Text("Reset") }
            }
        }
    }
}
