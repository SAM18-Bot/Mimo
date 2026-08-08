package com.mimo.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.mimo.app.network.WebSocketManager
import com.mimo.app.ui.components.AssignmentList
import com.mimo.app.ui.components.FocusScoreGauge
import com.mimo.app.ui.components.ScreenTimeBar
import com.mimo.app.ui.components.StatsRow
import com.mimo.app.ui.theme.MimoTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = viewModel()) {
    val stats by viewModel.stats.collectAsState()
    val assignments by viewModel.assignments.collectAsState()
    val history by viewModel.history.collectAsState()
    val screenBreakdown by viewModel.screenBreakdown.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val wsConnectionState by viewModel.wsConnectionState.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(error) {
        error?.let {
            snackbarHostState.showSnackbar(it)
        }
    }

    MimoTheme {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("Mimo") },
                    actions = {
                        IconButton(onClick = { viewModel.refresh() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                        }
                        val dotColor = when (wsConnectionState) {
                            WebSocketManager.ConnectionState.CONNECTED -> Color.Green
                            WebSocketManager.ConnectionState.RECONNECTING -> Color.Yellow
                            else -> Color.Red
                        }
                        Box(
                            modifier = Modifier
                                .padding(end = 16.dp)
                                .size(12.dp)
                                .clip(CircleShape)
                                .background(dotColor)
                        )
                    }
                )
            },
            snackbarHost = { SnackbarHost(snackbarHostState) }
        ) { paddingValues ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
            ) {
                Column(
                    modifier = Modifier
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

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = "Tasks",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.Bold
                        )
                        AssignmentList(
                            assignments = assignments,
                            onMarkDone = { id -> viewModel.markAssignmentDone(id) }
                        )
                    }
                }

                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
            }
        }
    }
}
