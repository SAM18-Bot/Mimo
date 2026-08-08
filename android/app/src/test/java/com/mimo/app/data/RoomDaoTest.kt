package com.mimo.app.data

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomDaoTest {

    private lateinit var database: MimoDatabase
    private lateinit var dailyStatsDao: DailyStatsDao
    private lateinit var assignmentDao: AssignmentDao

    @Before
    fun createDb() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            MimoDatabase::class.java
        ).allowMainThreadQueries().build()

        dailyStatsDao = database.dailyStatsDao()
        assignmentDao = database.assignmentDao()
    }

    @After
    fun closeDb() {
        database.close()
    }

    @Test
    fun dailyStatsDao_insertOrUpdate_preservesUnsyncedLocalRecordOnRemoteRefresh() = runBlocking {
        // Local user updates stats offline (isSynced = false)
        val localUnsynced = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 120,
            distractingMin = 30,
            neutralMin = 15,
            focusScore = 80.0,
            isSynced = false
        )
        dailyStatsDao.insertOrUpdate(localUnsynced)

        // Network refresh attempts to overwrite with stale server stats (isSynced = true)
        val remoteServerStats = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 0,
            distractingMin = 0,
            neutralMin = 0,
            focusScore = 0.0,
            isSynced = true
        )
        dailyStatsDao.insertOrUpdate(remoteServerStats)

        val retrieved = dailyStatsDao.getByDate("2026-08-07")
        assertNotNull(retrieved)
        assertEquals(120, retrieved?.productiveMin)
        assertEquals(30, retrieved?.distractingMin)
        assertFalse(retrieved?.isSynced ?: true)
    }

    @Test
    fun dailyStatsDao_insertOrUpdate_overwritesSyncedLocalRecordOnRemoteRefresh() = runBlocking {
        // Synced local record (isSynced = true)
        val localSynced = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 60,
            distractingMin = 20,
            isSynced = true
        )
        dailyStatsDao.insertOrUpdate(localSynced)

        // Remote refresh with updated stats (isSynced = true)
        val remoteStats = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 150,
            distractingMin = 10,
            isSynced = true
        )
        dailyStatsDao.insertOrUpdate(remoteStats)

        val retrieved = dailyStatsDao.getByDate("2026-08-07")
        assertNotNull(retrieved)
        assertEquals(150, retrieved?.productiveMin)
        assertTrue(retrieved?.isSynced ?: false)
    }

    @Test
    fun dailyStatsDao_insertOrUpdate_allowsLocalEditOnUnsyncedRecord() = runBlocking {
        val initialLocal = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 30,
            isSynced = false
        )
        dailyStatsDao.insertOrUpdate(initialLocal)

        // Additional local offline activity update (isSynced = false)
        val updatedLocal = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 60,
            isSynced = false
        )
        dailyStatsDao.insertOrUpdate(updatedLocal)

        val retrieved = dailyStatsDao.getByDate("2026-08-07")
        assertNotNull(retrieved)
        assertEquals(60, retrieved?.productiveMin)
        assertFalse(retrieved?.isSynced ?: true)
    }

    @Test
    fun dailyStatsDao_getUnsynced_and_markSynced() = runBlocking {
        val stats1 = DailyStatsEntity(date = "2026-08-07", productiveMin = 10, isSynced = false)
        val stats2 = DailyStatsEntity(date = "2026-08-08", productiveMin = 20, isSynced = false)
        val stats3 = DailyStatsEntity(date = "2026-08-06", productiveMin = 30, isSynced = true)

        dailyStatsDao.insertOrUpdate(stats1)
        dailyStatsDao.insertOrUpdate(stats2)
        dailyStatsDao.insertOrUpdate(stats3)

        val unsyncedBefore = dailyStatsDao.getUnsynced()
        assertEquals(2, unsyncedBefore.size)

        dailyStatsDao.markSynced(listOf("2026-08-07", "2026-08-08"))
        val unsyncedAfter = dailyStatsDao.getUnsynced()
        assertTrue(unsyncedAfter.isEmpty())
    }

    @Test
    fun assignmentDao_insert_preservesUnsyncedLocalAssignmentOnRemoteRefresh() = runBlocking {
        // Initial synced assignment from server
        val syncedAssignment = AssignmentEntity(
            id = 1,
            title = "Math Homework",
            dueDate = "2026-08-10",
            status = "pending",
            isSynced = true
        )
        assignmentDao.insert(syncedAssignment)

        // User marks assignment done offline -> updates status and sets isSynced = false
        assignmentDao.markDone(1)

        val edited = assignmentDao.getById(1)
        assertNotNull(edited)
        assertEquals("done", edited?.status)
        assertFalse(edited?.isSynced ?: true)

        // Server refresh returns assignment with old "pending" status (isSynced = true)
        val remoteRefreshList = listOf(
            AssignmentEntity(
                id = 1,
                title = "Math Homework",
                dueDate = "2026-08-10",
                status = "pending",
                isSynced = true
            )
        )
        assignmentDao.insertAll(remoteRefreshList)

        // Verify local assignment remains status = "done" and isSynced = false
        val afterRefresh = assignmentDao.getById(1)
        assertNotNull(afterRefresh)
        assertEquals("done", afterRefresh?.status)
        assertFalse(afterRefresh?.isSynced ?: true)
    }

    @Test
    fun assignmentDao_insert_overwritesSyncedLocalAssignmentWithRemoteData() = runBlocking {
        val syncedAssignment = AssignmentEntity(
            id = 1,
            title = "Old Title",
            dueDate = "2026-08-10",
            status = "pending",
            isSynced = true
        )
        assignmentDao.insert(syncedAssignment)

        // Server updates assignment
        val remoteUpdate = AssignmentEntity(
            id = 1,
            title = "New Server Title",
            dueDate = "2026-08-10",
            status = "done",
            isSynced = true
        )
        assignmentDao.insert(remoteUpdate)

        val retrieved = assignmentDao.getById(1)
        assertNotNull(retrieved)
        assertEquals("New Server Title", retrieved?.title)
        assertEquals("done", retrieved?.status)
        assertTrue(retrieved?.isSynced ?: false)
    }

    @Test
    fun assignmentDao_markSynced_updatesIsSyncedToTrue() = runBlocking {
        val unsynced = AssignmentEntity(
            id = 0,
            title = "Local Task",
            dueDate = "2026-08-09",
            isSynced = false
        )
        val generatedId = assignmentDao.insert(unsynced).toInt()

        val unsyncedList = assignmentDao.getUnsynced()
        assertEquals(1, unsyncedList.size)
        assertEquals(generatedId, unsyncedList[0].id)

        assignmentDao.markSynced(listOf(generatedId))
        val unsyncedAfter = assignmentDao.getUnsynced()
        assertTrue(unsyncedAfter.isEmpty())
    }
}
