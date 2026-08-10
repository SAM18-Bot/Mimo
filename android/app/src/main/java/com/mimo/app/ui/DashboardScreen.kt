package com.mimo.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
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
import com.mimo.app.ui.components.ScheduleList
import com.mimo.app.ui.components.ScreenTimeBar
import com.mimo.app.ui.components.StatsRow
import com.mimo.app.ui.theme.MimoTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = viewModel()) {
    val stats by viewModel.stats.collectAsState()
    val assignments by viewModel.assignments.collectAsState()
    val schedule by viewModel.schedule.collectAsState()
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

    var showAddDialog by remember { mutableStateOf(false) }

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
            floatingActionButton = {
                FloatingActionButton(onClick = { showAddDialog = true }) {
                    Icon(Icons.Default.Add, contentDescription = "Add Assignment")
                }
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
                            text = "Today's Schedule",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.Bold
                        )
                        ScheduleList(schedule = schedule)
                    }

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = "Assignments",
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

            if (showAddDialog) {
                var newTitle by remember { mutableStateOf("") }
                var newSubject by remember { mutableStateOf("") }
                var newDueDate by remember { mutableStateOf("") }
                var newPriority by remember { mutableStateOf("medium") }

                AlertDialog(
                    onDismissRequest = { showAddDialog = false },
                    title = { Text("Add Assignment") },
                    text = {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = newTitle,
                                onValueChange = { newTitle = it },
                                label = { Text("Title") }
                            )
                            OutlinedTextField(
                                value = newSubject,
                                onValueChange = { newSubject = it },
                                label = { Text("Subject (Optional)") }
                            )
                            OutlinedTextField(
                                value = newDueDate,
                                onValueChange = { newDueDate = it },
                                label = { Text("Due Date (YYYY-MM-DD)") }
                            )
                            OutlinedTextField(
                                value = newPriority,
                                onValueChange = { newPriority = it },
                                label = { Text("Priority (high/medium/low)") }
                            )
                        }
                    },
                    confirmButton = {
                        TextButton(
                            onClick = {
                                viewModel.addAssignment(
                                    title = newTitle,
                                    subject = newSubject.ifBlank { null },
                                    dueDate = newDueDate.ifBlank { "2024-01-01" }, // Need a better default but fine for now
                                    priority = newPriority.ifBlank { "medium" }
                                )
                                showAddDialog = false
                            }
                        ) {
                            Text("Add")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { showAddDialog = false }) {
                            Text("Cancel")
                        }
                    }
                )
            }
        }
    }
}
