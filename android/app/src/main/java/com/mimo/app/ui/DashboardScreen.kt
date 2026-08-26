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
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Chat
import com.mimo.app.network.WebSocketManager
import com.mimo.app.ui.components.AssignmentList
import com.mimo.app.ui.components.TodoList
import com.mimo.app.ui.components.FocusScoreGauge
import com.mimo.app.ui.components.ScheduleList
import com.mimo.app.ui.components.ScreenTimeBar
import com.mimo.app.ui.components.StatsRow
import com.mimo.app.ui.theme.MimoTheme

import android.app.TimePickerDialog
import androidx.compose.ui.platform.LocalContext
import java.util.Calendar
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.time.ZoneOffset
import androidx.compose.foundation.clickable

@Composable
fun TimePickerField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    OutlinedTextField(
        value = value,
        onValueChange = {},
        label = { Text(label) },
        readOnly = true,
        modifier = modifier.clickable {
            val calendar = Calendar.getInstance()
            TimePickerDialog(
                context,
                { _, hourOfDay, minute ->
                    val isPM = hourOfDay >= 12
                    val displayHour = if (hourOfDay % 12 == 0) 12 else hourOfDay % 12
                    val amPm = if (isPM) "PM" else "AM"
                    val minStr = minute.toString().padStart(2, '0')
                    onValueChange("$displayHour:$minStr $amPm")
                },
                calendar.get(Calendar.HOUR_OF_DAY),
                calendar.get(Calendar.MINUTE),
                false // 12-hour format
            ).show()
        },
        enabled = false,
        colors = OutlinedTextFieldDefaults.colors(
            disabledTextColor = MaterialTheme.colorScheme.onSurface,
            disabledBorderColor = MaterialTheme.colorScheme.outline,
            disabledLabelColor = MaterialTheme.colorScheme.onSurfaceVariant
        )
    )
}

fun parse12HourToIso(timeStr: String): String? {
    if (timeStr.isBlank()) return null
    try {
        val formatter = DateTimeFormatter.ofPattern("h:mm a")
        val parsedTime = java.time.LocalTime.parse(timeStr.uppercase(), formatter)
        var dateTime = LocalDateTime.now().withHour(parsedTime.hour).withMinute(parsedTime.minute).withSecond(0).withNano(0)
        if (dateTime.isBefore(LocalDateTime.now())) {
            dateTime = dateTime.plusDays(1)
        }
        return dateTime.atOffset(ZoneOffset.UTC).format(DateTimeFormatter.ISO_INSTANT)
    } catch (e: Exception) {
        return null
    }
}


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = viewModel()) {
    val stats by viewModel.stats.collectAsState()
    val assignments by viewModel.assignments.collectAsState()
    val todos by viewModel.todos.collectAsState()
    val schedule by viewModel.schedule.collectAsState()
    val screenBreakdown by viewModel.screenBreakdown.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val wsConnectionState by viewModel.wsConnectionState.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.coachMessage.collect { msg ->
            snackbarHostState.showSnackbar(msg)
        }
    }

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
                Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    var showCoachDialog by remember { mutableStateOf(false) }
                    FloatingActionButton(onClick = { showCoachDialog = true }, containerColor = MaterialTheme.colorScheme.secondaryContainer) {
                        Icon(Icons.Default.Chat, contentDescription = "Ask Coach")
                    }
                    FloatingActionButton(onClick = { showAddDialog = true }) {
                        Icon(Icons.Default.Add, contentDescription = "Add Assignment")
                    }
                    
                    if (showCoachDialog) {
                        var commandText by remember { mutableStateOf("") }
                        AlertDialog(
                            onDismissRequest = { showCoachDialog = false },
                            title = { Text("Ask Coach") },
                            text = {
                                OutlinedTextField(
                                    value = commandText,
                                    onValueChange = { commandText = it },
                                    label = { Text("e.g. What should I study?") }
                                )
                            },
                            confirmButton = {
                                TextButton(onClick = {
                                    if (commandText.isNotBlank()) {
                                        viewModel.sendVoiceCommand(commandText) { }
                                    }
                                    showCoachDialog = false
                                }) { Text("Ask") }
                            },
                            dismissButton = {
                                TextButton(onClick = { showCoachDialog = false }) { Text("Cancel") }
                            }
                        )
                    }
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
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = "To-Do List",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.Bold
                        )
                        TodoList(
                            todos = todos,
                            onMarkDone = { id -> viewModel.markTodoDone(id) }
                        )
                        
                        var newTodoTitle by remember { mutableStateOf("") }
                        var newTodoTime by remember { mutableStateOf("") }
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                            OutlinedTextField(
                                value = newTodoTitle,
                                onValueChange = { newTodoTitle = it },
                                label = { Text("Task") },
                                modifier = Modifier.weight(1f)
                            )
                            Spacer(Modifier.width(8.dp))
                            TimePickerField(
                                value = newTodoTime,
                                onValueChange = { newTodoTime = it },
                                label = "Time",
                                modifier = Modifier.width(100.dp)
                            )
                            IconButton(onClick = {
                                if (newTodoTitle.isNotBlank()) {
                                    val remindAt = parse12HourToIso(newTodoTime)
                                    viewModel.addTodo(newTodoTitle, null, remindAt)
                                    newTodoTitle = ""
                                    newTodoTime = ""
                                }
                            }) {
                                Icon(Icons.Default.Add, contentDescription = "Add Todo")
                            }
                        }
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
                var newDueTime by remember { mutableStateOf("") }
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
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = newDueDate,
                                    onValueChange = { newDueDate = it },
                                    label = { Text("Date (YYYY-MM-DD)") },
                                    modifier = Modifier.weight(1f)
                                )
                                TimePickerField(
                                    value = newDueTime,
                                    onValueChange = { newDueTime = it },
                                    label = "Time",
                                    modifier = Modifier.weight(1f)
                                )
                            }
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
                                    dueDate = newDueDate.ifBlank { "2024-01-01" }, // Need better default
                                    dueTime = newDueTime.ifBlank { null },
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
