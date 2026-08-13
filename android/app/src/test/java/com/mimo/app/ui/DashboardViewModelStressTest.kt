package com.mimo.app.ui

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.data.AssignmentDao
import com.mimo.app.data.DailyStatsDao
import com.mimo.app.data.DailyStatsEntity
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.Assignment
import com.mimo.app.network.DailyStats
import com.mimo.app.network.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(AndroidJUnit4::class)
class DashboardViewModelStressTest {

    private lateinit var database: MimoDatabase
    private lateinit var assignmentDao: AssignmentDao
    private lateinit var dailyStatsDao: DailyStatsDao
    private val testDispatcher = StandardTestDispatcher()
    private lateinit var fakeApiService: FakeMimoApiService

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            MimoDatabase::class.java
        )
            .allowMainThreadQueries()
            .setQueryExecutor(testDispatcher.asExecutor())
            .setTransactionExecutor(testDispatcher.asExecutor())
            .build()

        assignmentDao = database.assignmentDao()
        dailyStatsDao = database.dailyStatsDao()
        fakeApiService = FakeMimoApiService(shouldThrowError = true)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        database.close()
    }

    @Test
    fun viewModel_highFrequencyUpdates_maintainsDataIntegrity() = runTest {
        var currentDate = "2026-08-07"
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { currentDate },
            webSocketManager = null,
            apiService = fakeApiService
        )

        // Subscribe to stats StateFlow to activate WhileSubscribed
        val collectJob = backgroundScope.launch { viewModel.stats.collect {} }

        // Perform sequential updates to stats
        for (i in 1..10) {
            viewModel.updateStats(productiveDelta = 2, distractingDelta = 1, neutralDelta = 0)
            testScheduler.advanceUntilIdle()
        }

        val stats = dailyStatsDao.getByDate("2026-08-07")
        assertNotNull(stats)
        assertEquals(20, stats?.productiveMin)
        assertEquals(10, stats?.distractingMin)
        assertFalse(stats?.isSynced ?: true)
        collectJob.cancel()
    }

    @Test
    fun viewModel_dateRollover_reactivelySwitchesStatsFlow() = runTest {
        var currentDate = "2026-08-07"
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { currentDate },
            webSocketManager = null,
            apiService = fakeApiService
        )

        // Subscribe to stats StateFlow to activate WhileSubscribed
        val collectJob = backgroundScope.launch { viewModel.stats.collect {} }

        // Initial state for Aug 7
        viewModel.updateStats(productiveDelta = 30, distractingDelta = 10)
        testScheduler.advanceUntilIdle()

        assertEquals("2026-08-07", viewModel.stats.value.date)
        assertEquals(30, viewModel.stats.value.productive_min)

        // Seed DB for Aug 8
        dailyStatsDao.insertOrUpdate(
            DailyStatsEntity(
                date = "2026-08-08",
                productiveMin = 90,
                distractingMin = 5,
                focusScore = 94.7,
                isSynced = false
            )
        )

        // Simulate midnight rollover
        currentDate = "2026-08-08"
        testScheduler.advanceTimeBy(61_000) // Trigger 60s periodic tick in currentDateFlow
        testScheduler.runCurrent()

        assertEquals("2026-08-08", viewModel.stats.value.date)
        assertEquals(90, viewModel.stats.value.productive_min)
        collectJob.cancel()
    }

    @Test
    fun viewModel_rapidAssignmentCreationAndCompletion_flowEmitsCorrectList() = runTest {
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-07" },
            webSocketManager = null,
            apiService = fakeApiService
        )

        // Subscribe to assignments StateFlow to activate WhileSubscribed
        val collectJob = backgroundScope.launch { viewModel.assignments.collect {} }

        // Add 10 assignments
        for (i in 1..10) {
            viewModel.addAssignment("Task $i", "Subject $i", "2026-08-10")
            testScheduler.advanceUntilIdle()
        }

        val list = viewModel.assignments.value
        assertEquals(10, list.size)

        // Mark odd IDs as done
        val unsyncedList = assignmentDao.getUnsynced()
        for (task in unsyncedList) {
            if (task.id % 2 != 0) {
                viewModel.markAssignmentDone(task.id)
                testScheduler.advanceUntilIdle()
            }
        }

        val updatedList = viewModel.assignments.value
        val doneCount = updatedList.count { it.status == "done" }
        assertEquals(5, doneCount)
        collectJob.cancel()
    }

    @Test
    fun viewModel_refresh_handlesMultipleExceptionTypesResiliently() = runTest {
        val throwingApiService = object : MimoApiService {
            override suspend fun login(body: LoginRequest): AuthResponse {
                throw UnsupportedOperationException()
            }

            override suspend fun register(body: RegisterRequest): AuthResponse {
                throw UnsupportedOperationException()
            }

            override suspend fun completeOnboarding(body: OnboardingRequest): UserOut {
                throw UnsupportedOperationException()
            }

            override suspend fun authenticateGoogle(body: Map<String, String>): Map<String, Any> {
                throw UnsupportedOperationException()
            }

            override suspend fun getStats(targetDate: String?): DailyStats {
                throw RuntimeException("Fatal server error 500")
            }

            override suspend fun getHistory(days: Int): List<DailyHistoryItem> {
                throw IllegalStateException("Malformed JSON response")
            }

            override suspend fun getAssignments(status: String?): List<Assignment> {
                throw IOException("Socket timeout")
            }

            override suspend fun createAssignment(assignment: com.mimo.app.network.AssignmentCreate): Assignment {
                throw UnsupportedOperationException()
            }

            override suspend fun markAssignmentDone(id: Int): Map<String, Any> {
                throw UnsupportedOperationException()
            }

            override suspend fun getSchedule(): List<ScheduleBlock> {
                throw UnsupportedOperationException()
            }

            override suspend fun getScheduleToday(): List<ScheduleBlock> {
                throw UnsupportedOperationException()
            }

            override suspend fun getScreenBreakdown(targetDate: String?): ScreenBreakdown {
                throw RuntimeException("Database timeout")
            }

            override suspend fun syncMockScreen(body: MockWindowEvent): Map<String, Any> {
                throw UnsupportedOperationException()
            }

            override suspend fun pushSync(payload: SyncPayload): Map<String, Any> {
                throw UnsupportedOperationException()
            }

            override suspend fun pullSync(): SyncPayload {
                throw UnsupportedOperationException()
            }
        }

        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-07" },
            webSocketManager = null,
            apiService = throwingApiService
        )

        // Refresh should catch all non-cancellation exceptions without throwing or crashing
        viewModel.refresh()
        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.isLoading.value)
    }
}
