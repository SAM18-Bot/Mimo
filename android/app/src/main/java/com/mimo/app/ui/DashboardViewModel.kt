package com.mimo.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.mimo.app.MimoApplication
import com.mimo.app.data.AssignmentDao
import com.mimo.app.data.AssignmentEntity
import com.mimo.app.data.DailyStatsDao
import com.mimo.app.data.DailyStatsEntity
import com.mimo.app.data.MimoDatabase
import com.mimo.app.data.toDomain
import com.mimo.app.data.toEntity
import com.mimo.app.network.*
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModel @JvmOverloads constructor(
    application: Application = MimoApplication.instance,
    private val assignmentDao: AssignmentDao = MimoDatabase.getDatabase(application).assignmentDao(),
    private val dailyStatsDao: DailyStatsDao = MimoDatabase.getDatabase(application).dailyStatsDao(),
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val dateProvider: () -> String = {
        SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
    },
    private val webSocketManager: WebSocketManager? = null,
    apiService: MimoApiService? = null
) : AndroidViewModel(application) {

    private val apiService: MimoApiService = apiService ?: ApiClient.api

    private fun getTodayDateString(): String = dateProvider()

    // Dynamic date flow emitting the current date and ticking periodically to catch date rollover
    private val currentDateFlow: Flow<String> = flow {
        while (true) {
            emit(getTodayDateString())
            delay(60_000)
        }
    }.distinctUntilChanged()

    val stats: StateFlow<DailyStats> = currentDateFlow
        .flatMapLatest { dateStr ->
            dailyStatsDao.getByDateFlow(dateStr).map { entity ->
                entity?.toDomain() ?: DailyStats(date = dateStr)
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = DailyStats(date = getTodayDateString())
        )

    val assignments: StateFlow<List<Assignment>> = assignmentDao.getAllAssignments()
        .map { entities -> entities.map { it.toDomain() } }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    private val _schedule = MutableStateFlow<List<ScheduleBlock>>(emptyList())
    val schedule: StateFlow<List<ScheduleBlock>> = _schedule.asStateFlow()

    private val _history = MutableStateFlow<List<DailyHistoryItem>>(emptyList())
    val history: StateFlow<List<DailyHistoryItem>> = _history.asStateFlow()

    private val _screenBreakdown = MutableStateFlow(ScreenBreakdown())
    val screenBreakdown: StateFlow<ScreenBreakdown> = _screenBreakdown.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _wsConnectionState = MutableStateFlow(WebSocketManager.ConnectionState.DISCONNECTED)
    val wsConnectionState: StateFlow<WebSocketManager.ConnectionState> = _wsConnectionState.asStateFlow()

    init {
        refresh()
        webSocketManager?.connect()
        webSocketManager?.let { ws ->
            viewModelScope.launch(ioDispatcher) {
                ws.connectionState.collect { state ->
                    _wsConnectionState.value = state
                }
            }
            viewModelScope.launch(ioDispatcher) {
                ws.events.collect { event ->
                    when (event.type) {
                        "stats_update" -> event.stats?.let { remoteStats ->
                            dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))
                        }
                        "tasks_list" -> event.tasks?.let { remoteTasks ->
                            assignmentDao.insertAll(remoteTasks.map { it.toEntity(isSynced = true) })
                        }
                        "assignment_done", "assignment_added", "assignment_updated", "schedule_updated" -> refresh()
                    }
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager?.disconnect()
    }

    fun refresh() {
        viewModelScope.launch(ioDispatcher) {
            _isLoading.value = true
            _error.value = null
            try {
                try {
                    val remoteStats = apiService.getStats()
                    dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))
                } catch (e: Exception) {
                    if (e is kotlinx.coroutines.CancellationException) throw e
                    // Network exception on stats - proceed offline
                }

                try {
                    val remoteAssignments = apiService.getAssignments()
                    assignmentDao.insertAll(remoteAssignments.map { it.toEntity(isSynced = true) })
                } catch (e: Exception) {
                    if (e is kotlinx.coroutines.CancellationException) throw e
                    // Network exception on assignments - proceed offline
                }

                try {
                    _schedule.value = apiService.getSchedule()
                } catch (e: Exception) {
                    if (e is kotlinx.coroutines.CancellationException) throw e
                    try {
                        _schedule.value = apiService.getScheduleToday()
                    } catch (e2: Exception) {
                        if (e2 is kotlinx.coroutines.CancellationException) throw e2
                    }
                }

                try {
                    _history.value = apiService.getHistory()
                } catch (e: Exception) {
                    if (e is kotlinx.coroutines.CancellationException) throw e
                }

                try {
                    _screenBreakdown.value = apiService.getScreenBreakdown()
                } catch (e: Exception) {
                    if (e is kotlinx.coroutines.CancellationException) throw e
                }
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                // Top-level network exception handler for offline resilience
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun addAssignment(
        title: String,
        subject: String? = null,
        dueDate: String = getTodayDateString(),
        priority: String = "medium",
        notes: String? = null
    ) {
        viewModelScope.launch(ioDispatcher) {
            val entity = AssignmentEntity(
                title = title,
                subject = subject,
                dueDate = dueDate,
                priority = priority,
                status = "pending",
                notes = notes,
                isSynced = false
            )
            assignmentDao.insert(entity)
        }
    }

    fun markAssignmentDone(id: Int) {
        viewModelScope.launch(ioDispatcher) {
            assignmentDao.markDone(id)
            runCatching { apiService.markAssignmentDone(id) }
        }
    }

    fun updateStats(productiveDelta: Int, distractingDelta: Int, neutralDelta: Int = 0) {
        viewModelScope.launch(ioDispatcher) {
            val today = getTodayDateString()
            val currentEntity = dailyStatsDao.getByDate(today)
            val prod = (currentEntity?.productiveMin ?: 0) + productiveDelta
            val dist = (currentEntity?.distractingMin ?: 0) + distractingDelta
            val neut = (currentEntity?.neutralMin ?: 0) + neutralDelta
            val total = prod + dist + neut
            val score = if (total > 0) {
                (prod.toDouble() / (prod + dist).coerceAtLeast(1)) * 100.0
            } else {
                0.0
            }

            val updatedEntity = DailyStatsEntity(
                date = today,
                productiveMin = prod,
                distractingMin = dist,
                neutralMin = neut,
                focusScore = score,
                isSynced = false
            )
            dailyStatsDao.insertOrUpdate(updatedEntity)
        }
    }
}
