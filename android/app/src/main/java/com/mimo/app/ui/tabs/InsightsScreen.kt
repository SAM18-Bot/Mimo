package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mimo.app.ui.DashboardViewModel

@Composable
fun InsightsScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier) {
    val history by viewModel.history.collectAsState()
    val recommendations by viewModel.studyRecommendations.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        Text("Insights", style = MaterialTheme.typography.headlineMedium)

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Weekly Focus Trend", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(16.dp))
                if (history.isEmpty()) {
                    Text("No history data available yet.", style = MaterialTheme.typography.bodyMedium)
                } else {
                    history.forEach { day ->
                        Text("${day.date}: ${day.productive_min}m focus", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("AI Study Recommendations", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(16.dp))
                val recList = recommendations?.recommendations
                if (recList.isNullOrEmpty()) {
                    Text("No recommendations available yet. Keep studying!", style = MaterialTheme.typography.bodyMedium)
                } else {
                    recList.forEach { rec ->
                        Text("• $rec", style = MaterialTheme.typography.bodyMedium)
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }
            }
        }
    }
}
