package com.mimo.app.ui.tabs

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.unit.dp
import com.mimo.app.network.*
import com.mimo.app.ui.DashboardViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import retrofit2.http.GET

data class LiveWindow(val app: String = "", val title: String = "", val category: String = "")
data class Presence(val status: String = "")
data class Roast(val message: String = "")
interface LiveApi {
    @GET("screen/live") suspend fun window(): LiveWindow
    @GET("cv/presence") suspend fun presence(): Presence
    @GET("reports/roasts") suspend fun roasts(): List<Roast>
}

@Composable
fun LiveActivity(vm: DashboardViewModel, breakdown: ScreenBreakdown, stats: DailyStats) {
    val api = remember { ApiClient.createService(LiveApi::class.java) }
    var windows by remember { mutableStateOf(emptyList<LiveWindow>()) }
    var presence by remember { mutableStateOf("offline") }
    var roasts by remember { mutableStateOf(emptyList<Roast>()) }
    var feedback by remember { mutableStateOf<String?>(null) }
    var refresh by remember { mutableIntStateOf(0) }
    val socket by vm.wsConnectionState.collectAsState()
    LaunchedEffect(refresh) {
        try {
            val current = api.window()
            if (windows.isEmpty() && current.app != "Unknown") windows = listOf(current)
            presence = api.presence().status
            roasts = api.roasts().take(10)
            feedback = null
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) { feedback = "Live activity could not be loaded." }
    }
    LaunchedEffect(vm) {
        vm.liveEvents.collect { event ->
            when (event.type) {
                "window_change" -> windows = (listOf(LiveWindow(event.app.orEmpty(), event.title.orEmpty(), event.category.orEmpty())) + windows).take(8)
                "cv_event" -> presence = event.event ?: presence
                "roast" -> event.message?.let { roasts = (listOf(Roast(it)) + roasts).take(10) }
            }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("Live activity", style = MaterialTheme.typography.titleLarge)
        Text("Connection: ${socket.name.lowercase()} · Desk presence: $presence")
        Text("Distractions: ${stats.distraction_count} · Absences: ${stats.absent_count} · Longest focus: ${stats.longest_focus_min}m")
        windows.forEach { w -> Text(listOf(w.app, w.title, w.category).filter { it.isNotBlank() }.joinToString(" · ")) }
        breakdown.top_productive.orEmpty().forEach { Text("Productive · ${it.app} · ${it.minutes}m") }
        breakdown.top_distracting.orEmpty().forEach { Text("Distracting · ${it.app} · ${it.minutes}m") }
        if (roasts.isNotEmpty()) Text("Recent coach alerts", style = MaterialTheme.typography.titleMedium)
        roasts.forEach { Text(it.message) }
        feedback?.let { Text(it) }
        TextButton(onClick = { refresh++; vm.refresh() }) { Text("Refresh activity") }
    }
}
