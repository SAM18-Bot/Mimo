package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.mimo.app.ui.DashboardViewModel
import com.mimo.app.ui.components.AssignmentList
import com.mimo.app.ui.components.TodoList
import com.mimo.app.ui.TimePickerField
import com.mimo.app.ui.parse12HourToIso

@Composable
fun ScheduleScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier, initialSubject: String? = null,
                   onInitialSubjectHandled: () -> Unit = {}) {
    val assignments by viewModel.assignments.collectAsState()
    val todos by viewModel.todos.collectAsState()

    var showAddDialog by remember { mutableStateOf(false) }

    Box(modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, top = 16.dp, end = 16.dp, bottom = 88.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            com.mimo.app.ui.planner.WeeklyPlanner(initialSubject, onInitialSubjectHandled, viewModel::refresh)

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Assignments", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                AssignmentList(
                    assignments = assignments,
                    onMarkDone = { id -> viewModel.markAssignmentDone(id) }
                )
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("To-Do List", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                TodoList(
                    todos = todos,
                    onMarkDone = { id -> viewModel.markTodoDone(id) }
                )

                var newTodoTitle by remember { mutableStateOf("") }
                var newTodoTime by remember { mutableStateOf("") }
                var savingTodo by remember { mutableStateOf(false) }
                val focus = LocalFocusManager.current
                fun submitTodo() {
                    val title = newTodoTitle.trim()
                    if (savingTodo || title.isEmpty() || title.length > 300) return
                    savingTodo = true
                    focus.clearFocus()
                    viewModel.addTodo(title, null, parse12HourToIso(newTodoTime)) { saved ->
                        savingTodo = false
                        if (saved) {
                            newTodoTitle = ""
                            newTodoTime = ""
                        }
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(
                        value = newTodoTitle,
                        onValueChange = { newTodoTitle = it },
                        label = { Text("Task") },
                        enabled = !savingTodo,
                        singleLine = true,
                        isError = newTodoTitle.trim().length > 300,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                        keyboardActions = KeyboardActions(onDone = { submitTodo() }),
                        modifier = Modifier.weight(1f)
                    )
                    Spacer(Modifier.width(8.dp))
                    TimePickerField(
                        value = newTodoTime,
                        onValueChange = { if (!savingTodo) newTodoTime = it },
                        label = "Time",
                        modifier = Modifier.width(100.dp)
                    )
                }
                if (newTodoTitle.trim().length > 300) {
                    Text("Use a task title of up to 300 characters.", color = MaterialTheme.colorScheme.error)
                }
                Button(enabled = !savingTodo && newTodoTitle.trim().length in 1..300, onClick = ::submitTodo) {
                    Text(if (savingTodo) "Saving…" else "Add to-do")
                }
            }
        }
        
        FloatingActionButton(
            onClick = { showAddDialog = true },
            modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp)
        ) {
            Icon(Icons.Default.Add, contentDescription = "Add Assignment")
        }

        if (showAddDialog) {
            var newTitle by remember { mutableStateOf("") }
            var newSubject by remember { mutableStateOf("") }
            var newDueDate by remember { mutableStateOf(java.time.LocalDate.now().plusDays(1).toString()) }
            var newDueTime by remember { mutableStateOf("") }
            var newPriority by remember { mutableStateOf("medium") }

            AlertDialog(
                onDismissRequest = { showAddDialog = false },
                title = { Text("Add Assignment") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(value = newTitle, onValueChange = { newTitle = it }, label = { Text("Title") })
                        OutlinedTextField(value = newSubject, onValueChange = { newSubject = it }, label = { Text("Subject") })
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(value = newDueDate, onValueChange = { newDueDate = it }, label = { Text("Date (YYYY-MM-DD)") }, modifier = Modifier.weight(1f))
                            TimePickerField(value = newDueTime, onValueChange = { newDueTime = it }, label = "Time", modifier = Modifier.weight(1f))
                        }
                        OutlinedTextField(value = newPriority, onValueChange = { newPriority = it }, label = { Text("Priority") })
                    }
                },
                confirmButton = {
                    TextButton(enabled = newTitle.isNotBlank() && newTitle.trim().length <= 300 && newSubject.trim().length <= 100 &&
                        newPriority.ifBlank { "medium" } in setOf("high","medium","low") && runCatching { java.time.LocalDate.parse(newDueDate.trim()) }.isSuccess, onClick = {
                        viewModel.addAssignment(
                            title = newTitle,
                            subject = newSubject.ifBlank { null },
                            dueDate = newDueDate.trim(),
                            dueTime = newDueTime.ifBlank { null },
                            priority = newPriority.ifBlank { "medium" }
                        )
                        showAddDialog = false
                    }) { Text("Add") }
                },
                dismissButton = {
                    TextButton(onClick = { showAddDialog = false }) { Text("Cancel") }
                }
            )
        }
    }
}
