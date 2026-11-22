package com.mimo.app.ui.planner

import android.app.DatePickerDialog
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.mimo.app.network.PlannerActivity
import com.mimo.app.network.PlannerSubject
import java.time.LocalDate

private val dayNames = listOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

@Composable
fun WeeklyPlanner(initialSubject: String?, handled: () -> Unit, refreshed: () -> Unit) {
    val planner: PlannerViewModel = viewModel()
    val context = LocalContext.current
    LaunchedEffect(Unit) { planner.refresh() }
    LaunchedEffect(initialSubject, planner.loaded) {
        if (initialSubject != null && planner.loaded) {
            planner.edit(initialSubject)
            handled()
        }
    }
    Text("Weekly schedule", style = MaterialTheme.typography.titleLarge)
    val date = planner.selectedDate
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        TextButton(onClick = { DatePickerDialog(context, { _, y, m, d -> planner.selectDate(LocalDate.of(y, m+1, d)) },
            date.year, date.monthValue - 1, date.dayOfMonth).show() }) { Text(date.toString()) }
        OutlinedButton(enabled = planner.loaded && !planner.busy, onClick = { planner.edit() }) { Text("Edit schedule") }
        TextButton(enabled = !planner.busy, onClick = planner::refresh) { Text("Refresh") }
    }
    val selectedBlocks = planner.week.filter {
        it.block_date == date.toString() || (it.block_date == null && it.day_of_week == date.dayOfWeek.value - 1)
    }.sortedBy { it.start_time }
    if (planner.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
    if (planner.loaded && selectedBlocks.isEmpty()) Text("No blocks scheduled for this day.")
    selectedBlocks.forEach { block ->
        Column {
            Text("${block.start_time}–${block.end_time}  ${block.title}", style = MaterialTheme.typography.titleMedium)
            Text(block.status)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("done" to "Complete", "skipped" to "Skip", "planned" to "Restore").filter { it.first != block.status }.forEach { (status,label) ->
                    TextButton(enabled = !planner.busy, onClick = { planner.changeStatus(block, status) }) { Text(label) }
                }
            }
        }
    }
    Row(Modifier.horizontalScroll(rememberScrollState())) {
        TextButton(enabled = !planner.busy, onClick = { planner.adjust(false) }) { Text("Boost deadline subjects") }
        TextButton(enabled = !planner.busy, onClick = { planner.adjust(true) }) { Text("Reschedule missed") }
        TextButton(enabled = !planner.busy, onClick = planner::loadSuggestions) { Text("Suggestions") }
    }
    planner.suggestions?.let { list -> if (list.isEmpty()) Text("No suggested changes.") else list.forEach { Text(it) } }
    var command by remember { mutableStateOf("") }
    OutlinedTextField(command, { command = it }, label = { Text("Quick add, e.g. Math due Friday at 5pm") },
        modifier = Modifier.fillMaxWidth())
    TextButton(enabled = command.isNotBlank() && !planner.busy, onClick = {
        planner.quickAdd(command, null) { command = ""; refreshed() }
    }) { Text("Add from text") }
    planner.feedback?.let { Text(it) }

    planner.draft?.let { draft ->
        AlertDialog(onDismissRequest = { if (!planner.busy) planner.draft = null }, title = { Text("Edit weekly schedule") },
            text = { ScheduleForm(draft) { planner.draft = it } },
            confirmButton = { Button(enabled = draft.validationError() == null && !planner.busy, onClick = planner::build) { Text("Save schedule") } },
            dismissButton = { TextButton(enabled = !planner.busy, onClick = { planner.draft = null }) { Text("Cancel") } })
    }
}

@Composable
private fun ScheduleForm(d: ScheduleDraft, change: (ScheduleDraft) -> Unit) {
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Field("Wake time (HH:MM)", d.wake) { change(d.copy(wake = it)) }
        Field("Sleep time (HH:MM)", d.sleep) { change(d.copy(sleep = it)) }
        Field("Time zone", d.timezone) { change(d.copy(timezone = it)) }
        Field("Daily goal (minutes)", d.goalMinutes) { change(d.copy(goalMinutes = it)) }
        Field("Session length (minutes)", d.sessionMinutes) { change(d.copy(sessionMinutes = it)) }
        Field("Break length (minutes)", d.breakMinutes) { change(d.copy(breakMinutes = it)) }
        Text("School days", style = MaterialTheme.typography.titleMedium)
        Row(Modifier.horizontalScroll(rememberScrollState())) {
            dayNames.forEachIndexed { index,label -> FilterChip(index in d.schoolDays, {
                change(d.copy(schoolDays = if (index in d.schoolDays) d.schoolDays - index else d.schoolDays + index))
            }, label = { Text(label) }) }
        }
        if (d.schoolDays.isNotEmpty()) {
            Field("School starts", d.schoolStart) { change(d.copy(schoolStart = it)) }
            Field("School ends", d.schoolEnd) { change(d.copy(schoolEnd = it)) }
        }
        Text("Subjects", style = MaterialTheme.typography.titleMedium)
        d.subjects.forEachIndexed { i, subject ->
            fun update(value: PlannerSubject) = change(d.copy(subjects = d.subjects.toMutableList().apply { set(i,value) }))
            Field("Subject", subject.name) { update(subject.copy(name = it)) }
            Row(Modifier.horizontalScroll(rememberScrollState())) {
                listOf("low","medium","high").forEach { priority ->
                    FilterChip(priority == subject.priority, { update(subject.copy(priority = priority)) }, label = { Text(priority) })
                }
                TextButton(onClick = { change(d.copy(subjects = d.subjects.filterIndexed { index,_ -> index != i })) }) { Text("Remove") }
            }
        }
        TextButton(onClick = { change(d.copy(subjects = d.subjects + PlannerSubject())) }) { Text("Add subject") }
        Text("Fixed activities", style = MaterialTheme.typography.titleMedium)
        d.activities.forEachIndexed { i, activity ->
            fun update(value: PlannerActivity) = change(d.copy(activities = d.activities.toMutableList().apply { set(i,value) }))
            Field("Activity", activity.title) { update(activity.copy(title = it)) }
            Row(Modifier.horizontalScroll(rememberScrollState())) {
                dayNames.forEachIndexed { index,label -> FilterChip(index == activity.day_of_week,
                    { update(activity.copy(day_of_week = index)) }, label = { Text(label) }) }
            }
            Field("Starts (HH:MM)", activity.start_time) { update(activity.copy(start_time = it)) }
            Field("Ends (HH:MM)", activity.end_time) { update(activity.copy(end_time = it)) }
            TextButton(onClick = { change(d.copy(activities = d.activities.filterIndexed { index,_ -> index != i })) }) { Text("Remove activity") }
        }
        TextButton(onClick = { change(d.copy(activities = d.activities + PlannerActivity())) }) { Text("Add activity") }
        Field("Year of study", d.year) { change(d.copy(year = it)) }
        Field("Primary goal", d.primaryGoal) { change(d.copy(primaryGoal = it)) }
        Field("Notes", d.notes) { change(d.copy(notes = it)) }
        d.validationError()?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}

@Composable
private fun Field(label: String, value: String, change: (String) -> Unit) {
    OutlinedTextField(value, change, label = { Text(label) }, modifier = Modifier.fillMaxWidth())
}
