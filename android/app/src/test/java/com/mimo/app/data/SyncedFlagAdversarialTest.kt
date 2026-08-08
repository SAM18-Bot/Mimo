package com.mimo.app.data

import com.mimo.app.network.Assignment
import com.mimo.app.network.DailyStats
import org.junit.Assert.*
import org.junit.Test

/**
 * Empirical Adversarial Tests for `isSynced` flag handling across CRUD operations and Sync logic.
 */
class SyncedFlagAdversarialTest {

    @Test
    fun testOfflineTaskCompletion_setsIsSyncedToFalse() {
        val originalEntity = AssignmentEntity(
            id = 1,
            title = "Assignment 1",
            status = "pending",
            dueDate = "2026-08-07",
            isSynced = true
        )
        assertTrue("Initial state must be synced", originalEntity.isSynced)

        // Simulating markDone operation
        val completedEntity = originalEntity.copy(status = "done", isSynced = false)

        assertFalse("Offline completion must set isSynced to false", completedEntity.isSynced)
        assertEquals("done", completedEntity.status)
    }

    @Test
    fun testRemoteRefresh_overwritesUnsyncedLocalTaskCompletion_demonstratingVulnerability() {
        // Step 1: Local assignment marked done offline (unsynced)
        val localUnsyncedAssignment = AssignmentEntity(
            id = 10,
            title = "Finish Lab Report",
            status = "done",
            dueDate = "2026-08-08",
            isSynced = false
        )

        // Step 2: Remote refresh receives server state where task is still pending
        val remoteServerAssignment = Assignment(
            id = 10,
            title = "Finish Lab Report",
            due_date = "2026-08-08",
            priority = "high",
            status = "pending",
            notes = null
        )

        // In DashboardViewModel.refresh(), it currently does:
        // assignmentDao.insertAll(remoteAssignments.map { it.toEntity(isSynced = true) })
        val refreshedEntity = remoteServerAssignment.toEntity(isSynced = true)

        // Adversarial Assertion:
        // The refreshed entity has status "pending" and isSynced = true!
        // When inserted into Room DB with OnConflictStrategy.REPLACE, localUnsyncedAssignment is overwritten!
        assertTrue("Refreshed entity forces isSynced = true", refreshedEntity.isSynced)
        assertEquals("pending", refreshedEntity.status)

        // Check if naive refresh preserves local unsynced state
        val isLocalUnsyncedStatePreserved = (refreshedEntity.status == localUnsyncedAssignment.status) &&
                (refreshedEntity.isSynced == localUnsyncedAssignment.isSynced)

        assertFalse(
            "FAIL: Naive remote refresh overwrites local unsynced task completion before sync!",
            isLocalUnsyncedStatePreserved
        )
    }

    @Test
    fun testRemoteRefresh_overwritesUnsyncedDailyStats_demonstratingVulnerability() {
        // Step 1: Local mobile tracking service logs 45 productive minutes offline
        val localUnsyncedStats = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 45,
            distractingMin = 15,
            neutralMin = 0,
            focusScore = 75.0,
            isSynced = false
        )

        // Step 2: Remote refresh receives server stats (where mobile time is 0)
        val remoteServerStats = DailyStats(
            date = "2026-08-07",
            productive_min = 0,
            distracting_min = 0,
            neutral_min = 0,
            focus_score = 0.0
        )

        // In DashboardViewModel.refresh(), it currently does:
        // dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))
        val refreshedEntity = remoteServerStats.toEntity(isSynced = true)

        // Adversarial Assertion:
        val isLocalStatsPreserved = (refreshedEntity.productiveMin == localUnsyncedStats.productiveMin) &&
                (refreshedEntity.isSynced == localUnsyncedStats.isSynced)

        assertFalse(
            "FAIL: Naive remote refresh overwrites local unsynced daily stats before sync!",
            isLocalStatsPreserved
        )
    }
}
