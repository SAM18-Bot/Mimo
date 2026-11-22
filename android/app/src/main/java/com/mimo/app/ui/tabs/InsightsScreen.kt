package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mimo.app.network.*
import com.mimo.app.ui.DashboardViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

@Composable
fun InsightsScreen(viewModel: DashboardViewModel, modifier: Modifier = Modifier, onTrackSubject: (String) -> Unit) {
    val history by viewModel.history.collectAsState()
    val breakdown by viewModel.screenBreakdown.collectAsState()
    val messages by viewModel.chatHistory.collectAsState()
    val api = remember { ApiClient.createService(CoachApi::class.java) }
    val scope = rememberCoroutineScope()
    var refresh by remember { mutableIntStateOf(0) }
    var advice by remember { mutableStateOf<StudyReport?>(null) }
    var report by remember { mutableStateOf<SavedReport?>(null) }
    var questions by remember { mutableStateOf(emptyList<String>()) }
    var answers by remember { mutableStateOf(emptyList<AccountabilityEntry>()) }
    var feedback by remember { mutableStateOf<String?>(null) }
    var generating by remember { mutableStateOf(false) }
    var sending by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf("") }
    var answer by remember { mutableStateOf("") }

    LaunchedEffect(refresh) {
        launch {
            try { advice = api.recommendations() } catch (e: CancellationException) { throw e }
            catch (_: Exception) { feedback = "Could not load study advice." }
        }
        launch {
            try { report = api.latest() } catch (e: CancellationException) { throw e }
            catch (_: Exception) { feedback = "Could not load the daily report." }
        }
        launch {
            try { questions = api.questions().questions; answers = api.answers() }
            catch (e: CancellationException) { throw e }
            catch (_: Exception) { feedback = "Could not load today's check-in." }
        }
    }
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Coach", style = MaterialTheme.typography.headlineMedium)
        messages.takeLast(20).forEach { msg -> Text("${if (msg.sender == "user") "You" else "Coach"} · ${msg.text}") }
        OutlinedTextField(draft, { draft = it }, label = { Text("Ask your coach") }, modifier = Modifier.fillMaxWidth())
        Button(enabled = !sending && draft.isNotBlank(), onClick = {
            sending = true
            viewModel.sendVoiceCommand(draft.trim()) { reply ->
                sending = false
                if (reply != null) draft = ""
            }
        }) { Text(if (sending) "Sending…" else "Send message") }
        HorizontalDivider()
        Text("Study advisor", style = MaterialTheme.typography.titleLarge)
        advice?.let { data ->
            data.recommendations.forEach { Text(it.recommendation) }
            data.daily_study_plan.forEach { Text("${it.start_time}–${it.end_time} · ${it.subject}") }
            data.suggested_subjects.forEach { subject -> OutlinedButton(onClick = { onTrackSubject(subject) }) { Text("Add $subject to schedule") } }
            data.weekly_patterns.forEach { Text(it) }
            if (data.recommendations.isEmpty() && data.daily_study_plan.isEmpty()) Text("No recommendations yet.")
        }
        Text("Weekly focus", style = MaterialTheme.typography.titleLarge)
        if (history.isEmpty()) Text("No daily summaries yet.")
        history.forEach { Text("${it.date} · ${it.focus_score.toInt()}/100 · ${it.productive_min}m productive") }
        breakdown.device_minutes.orEmpty().forEach { (device, minutes) ->
            Text("${if (device == "unknown") "Unspecified device" else device} · ${minutes}m")
        }
        HorizontalDivider()
        Text("Daily report", style = MaterialTheme.typography.titleLarge)
        if (report?.report.isNullOrEmpty()) Text("No report yet.")
        report?.date?.let { Text(it) }
        report?.report.orEmpty().forEach { (key, value) ->
            Text("${key.replace('_', ' ').replaceFirstChar(Char::uppercase)} · $value")
        }
        OutlinedButton(enabled = !generating, onClick = { scope.launch {
            generating = true
            try { report = api.generate() }
            catch (e: CancellationException) { throw e }
            catch (_: Exception) { feedback = "Could not generate the report. Refresh to check its status." }
            finally { generating = false }
        } }) { Text(if (generating) "Generating…" else "Generate daily report") }
        Text("Daily check-in", style = MaterialTheme.typography.titleLarge)
        answers.forEach { Text("${it.question}\n${it.answer}") }
        val question = questions.firstOrNull { q -> answers.none { it.question == q } }
        if (question != null) {
            Text(question)
            OutlinedTextField(answer, { answer = it }, label = { Text("Your answer") }, modifier = Modifier.fillMaxWidth())
            Button(enabled = !saving && answer.isNotBlank(), onClick = { scope.launch {
                saving = true
                val entry = AccountabilityEntry(question, answer.trim())
                try { api.answer(entry); answers = answers + entry; answer = "" }
                catch (e: CancellationException) { throw e }
                catch (_: Exception) { feedback = "Could not save your answer." }
                finally { saving = false }
            } }) { Text("Save answer") }
        }
        feedback?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        TextButton(onClick = { feedback = null; refresh++; viewModel.refresh() }) { Text("Refresh insights") }
    }
}
