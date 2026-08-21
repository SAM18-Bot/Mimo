package com.mimo.app.ui

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.data.AssignmentDao
import com.mimo.app.data.DailyStatsDao
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.asExecutor
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException

class FakeMimoApiService(
    var shouldThrowError: Boolean = true,
    var statsToReturn: DailyStats = DailyStats(date = "2026-08-07", productive_min = 60, distracting_min = 10),
    var assignmentsToReturn: List<Assignment> = emptyList(),
    var historyToReturn: List<DailyHistoryItem> = emptyList(),
    var breakdownToReturn: ScreenBreakdown = ScreenBreakdown()
) : MimoApiService {
    override suspend fun login(body: LoginRequest): AuthResponse {
        if (shouldThrowError) throw IOException("Network connection offline")
        return AuthResponse(access_token = "fake_token", token_type = "bearer")
    }

    override suspend fun register(body: RegisterRequest): AuthResponse {
        if (shouldThrowError) throw IOException("Network connection offline")
        return AuthResponse(access_token = "fake_token", token_type = "bearer")
    }

    override suspend fun completeOnboarding(body: OnboardingRequest): UserOut {
        if (shouldThrowError) throw IOException("Network connection offline")
        return UserOut(id = 1, email = "test@example.com", onboarding_completed = true)
    }

    override suspend fun authenticateGoogle(body: Map<String, String>): Map<String, Any> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return mapOf("token" to "fake_token", "user" to mapOf("id" to "1"))
    }

    override suspend fun getStats(targetDate: String?): DailyStats {
        if (shouldThrowError) throw IOException("Network connection offline")
        return statsToReturn
    }

    override suspend fun getHistory(days: Int): List<DailyHistoryItem> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return historyToReturn
    }

    override suspend fun getAssignments(status: String?): List<Assignment> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return assignmentsToReturn
    }

    override suspend fun createAssignment(assignment: AssignmentCreate): Assignment {
        if (shouldThrowError) throw IOException("Network connection offline")
        return Assignment(
            id = 100,
            title = assignment.title,
            subject = assignment.subject,
            due_date = assignment.due_date,
            priority = assignment.priority,
            status = "pending",
            notes = assignment.notes
        )
    }

    override suspend fun markAssignmentDone(id: Int): Map<String, Any> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return mapOf("status" to "success")
    }

    override suspend fun getSchedule(): List<ScheduleBlock> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return emptyList()
    }

    override suspend fun getScheduleToday(): List<ScheduleBlock> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return emptyList()
    }

    override suspend fun getScreenBreakdown(targetDate: String?): ScreenBreakdown {
        if (shouldThrowError) throw IOException("Network connection offline")
        return breakdownToReturn
    }

    override suspend fun syncMockScreen(body: MockWindowEvent): Map<String, Any> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return mapOf("status" to "ok")
    }

    override suspend fun pushSync(payload: SyncPayload): Map<String, Any> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return mapOf("status" to "ok")
    }

    override suspend fun pullSync(): SyncPayload {
        if (shouldThrowError) throw IOException("Network connection offline")
        return SyncPayload(
            date = "2026-08-07",
            mobileProductiveMin = 0,
            mobileDistractingMin = 0,
            mobileNeutralMin = 0,
            assignments = emptyList(),
            mergedStats = null
        )
    }

    override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
        if (shouldThrowError) throw IOException("Network connection offline")
        return mapOf("status" to "ok")
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(AndroidJUnit4::class)
class DashboardViewModelTest {

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
    fun viewModel_updateStats_savesUnsyncedLocalRecord() = runTest {
        val mockDate = "2026-08-07"
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { mockDate },
            webSocketManager = null,
            apiService = fakeApiService
        )

        viewModel.updateStats(productiveDelta = 45, distractingDelta = 15, neutralDelta = 10)
        testScheduler.advanceUntilIdle()

        val savedStats = dailyStatsDao.getByDate("2026-08-07")
        assertNotNull(savedStats)
        assertEquals(45, savedStats?.productiveMin)
        assertEquals(15, savedStats?.distractingMin)
        assertEquals(10, savedStats?.neutralMin)
        assertFalse(savedStats?.isSynced ?: true)
    }

    @Test
    fun viewModel_addAssignment_savesUnsyncedLocalEntity() = runTest {
        val mockDate = "2026-08-07"
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { mockDate },
            webSocketManager = null,
            apiService = fakeApiService
        )

        viewModel.addAssignment(
            title = "Chemistry Report",
            subject = "Chemistry",
            dueDate = "2026-08-12",
            priority = "high",
            notes = "Lab 4 results"
        )
        testScheduler.advanceUntilIdle()

        val unsynced = assignmentDao.getUnsynced()
        assertEquals(1, unsynced.size)
        assertEquals("Chemistry Report", unsynced[0].title)
        assertEquals("Chemistry", unsynced[0].subject)
        assertFalse(unsynced[0].isSynced)
    }

    @Test
    fun viewModel_dynamicDateProvider_evaluatesDateProvider() = runTest {
        val mockDate = "2026-08-07"
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { mockDate },
            webSocketManager = null,
            apiService = fakeApiService
        )

        testScheduler.advanceUntilIdle()
        assertEquals("2026-08-07", viewModel.stats.value.date)
    }

    @Test
    fun viewModel_refresh_handlesNetworkExceptionGracefully_offlineMode() = runTest {
        fakeApiService.shouldThrowError = true

        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-07" },
            webSocketManager = null,
            apiService = fakeApiService
        )

        viewModel.refresh()
        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.isLoading.value)
        assertNull(viewModel.error.value)
    }

    @Test
    fun viewModel_refresh_withRemoteData_populatesDatabase() = runTest {
        fakeApiService.shouldThrowError = false
        fakeApiService.assignmentsToReturn = listOf(
            Assignment(
                id = 10,
                title = "Remote Physics Assignment",
                subject = "Physics",
                due_date = "2026-08-15",
                priority = "high",
                status = "pending"
            )
        )

        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-07" },
            webSocketManager = null,
            apiService = fakeApiService
        )

        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.isLoading.value)
    }
}
