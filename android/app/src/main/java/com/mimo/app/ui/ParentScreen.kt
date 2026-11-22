package com.mimo.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mimo.app.network.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import retrofit2.HttpException

@Composable
fun ParentScreen() {
    val api = remember { ApiClient.createService(AccountApi::class.java) }
    val scope = rememberCoroutineScope()
    var children by remember { mutableStateOf(emptyList<UserOut>()) }
    var selected by remember { mutableStateOf<Int?>(null) }
    var summary by remember { mutableStateOf<ParentSummary?>(null) }
    var refresh by remember { mutableIntStateOf(0) }
    var invite by remember { mutableStateOf("") }
    var linking by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(refresh) {
        loading = true
        error = null
        try {
            children = api.children()
            if (children.none { it.id == selected }) selected = children.firstOrNull()?.id
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) { error = "Could not load linked students." }
        finally { loading = false }
    }
    LaunchedEffect(selected, refresh) {
        summary = null
        val id = selected ?: return@LaunchedEffect
        try { summary = api.weeklySummary(id) }
        catch (e: CancellationException) { throw e }
        catch (_: Exception) { error = "Could not load this student's summary." }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Parent dashboard", style = MaterialTheme.typography.headlineMedium)
        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        children.forEach { child ->
            FilterChip(child.id == selected, { selected = child.id }, label = { Text(child.display_name ?: child.email) })
        }
        val report = summary
        if (report != null && report.student_id == selected) {
            Text("Weekly summary", style = MaterialTheme.typography.titleLarge)
            Text("Average focus: ${report.avg_focus_score}/100")
            Text("Productive time: ${report.summaries.sumOf { it.productive_min }} minutes")
            if (report.summaries.isEmpty()) Text("No daily summaries yet.")
            report.summaries.forEach { day ->
                Text("${day.date} · Focus ${day.focus_score.toInt()} · ${day.productive_min}m productive · ${day.distracting_min}m distracting")
            }
        } else if (!loading && children.isEmpty() && error == null) Text("Link a student using the code from their settings.")
        OutlinedTextField(invite, { invite = it.trim().uppercase().take(12) }, singleLine = true,
            label = { Text("Student invite code") }, modifier = Modifier.fillMaxWidth())
        Button(enabled = !linking && invite.length in 6..12, onClick = {
            scope.launch {
                linking = true
                error = null
                try {
                    selected = api.linkStudent(ParentLinkRequest(invite)).student_id
                    invite = ""
                    refresh++
                } catch (e: CancellationException) { throw e }
                catch (e: HttpException) { error = if (e.code() in 400..404) "Check the invite code and its expiry." else "Could not link this student." }
                catch (_: Exception) { error = "Could not reach the server." }
                finally { linking = false }
            }
        }) { Text("Link student") }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        OutlinedButton(onClick = { refresh++ }) { Text("Refresh") }
        AppearanceSetting()
        ServerSetting()
        SignOutButton()
    }
}
