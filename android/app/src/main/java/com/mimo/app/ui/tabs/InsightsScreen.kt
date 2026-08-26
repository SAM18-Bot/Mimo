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
    // In a real app, we'd fetch this from viewModel, but for now we mock the UI 
    // to achieve parity quickly.
    
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
                // Mock chart
                Text("Monday: 4h 20m", style = MaterialTheme.typography.bodyMedium)
                Text("Tuesday: 3h 15m", style = MaterialTheme.typography.bodyMedium)
                Text("Wednesday: 5h 00m", style = MaterialTheme.typography.bodyMedium)
                Text("Thursday: 2h 45m", style = MaterialTheme.typography.bodyMedium)
                Text("Friday: 4h 10m", style = MaterialTheme.typography.bodyMedium)
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("AI Study Recommendations", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(16.dp))
                Text("• You should focus more on Calculus.", style = MaterialTheme.typography.bodyMedium)
                Text("• Try studying earlier in the day.", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
