package com.mimo.app.sync

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.data.AssignmentEntity
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.Assignment
import com.mimo.app.network.AssignmentCreate
import com.mimo.app.network.MimoApiService
import com.mimo.app.ui.FakeMimoApiService
import java.io.IOException
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AssignmentSyncTest {
    private lateinit var db: MimoDatabase

    @Before
    fun setUp() {
        db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), MimoDatabase::class.java)
            .allowMainThreadQueries().build()
    }

    @After
    fun tearDown() = db.close()

    @Test
    fun lostCreateResponseRetriesWithSameKeyAndCarriesLocalCompletion() = runBlocking {
        val dao = db.assignmentDao()
        val localId = dao.insertPending(AssignmentEntity(title = "Journal", dueDate = "2026-12-01", dueTime = "17:45"))
        val requests = mutableListOf<AssignmentCreate>()
        val completed = mutableListOf<Int>()
        val api = object : MimoApiService by FakeMimoApiService() {
            override suspend fun createAssignment(assignment: AssignmentCreate): Assignment {
                requests.add(assignment)
                if (requests.size == 1) throw IOException("Response lost after commit")
                return Assignment(id = 10, title = assignment.title, due_date = assignment.due_date,
                    due_time = assignment.due_time)
            }

            override suspend fun markAssignmentDone(id: Int): Map<String, Any> {
                completed.add(id)
                return mapOf("ok" to true)
            }
        }

        val first = dao.getById(localId)!!
        assertThrows(IOException::class.java) { runBlocking { uploadAssignment(dao, api, first) } }
        dao.markDone(localId)
        uploadAssignment(dao, api, dao.getById(localId)!!)

        assertEquals(2, requests.size)
        assertNotNull(requests.first().request_id)
        assertEquals(requests.first(), requests.last())
        assertEquals(listOf(10), completed)
        assertNull(dao.getById(localId))
        assertEquals("17:45", dao.getById(10)!!.dueTime)
        assertEquals("done", dao.getById(10)!!.status)
        assertTrue(dao.getUnsynced().isEmpty())
    }

    @Test
    fun delayedAcknowledgementCannotConsumeAnotherOfflineAssignment() = runBlocking {
        val dao = db.assignmentDao()
        val draft = AssignmentEntity(title = "First", dueDate = "2026-12-01")
        val localId = dao.insertPending(draft)
        val requestId = dao.getById(localId)!!.requestId!!
        val confirmed = draft.copy(id = 5, isSynced = true)
        dao.acknowledgeCreate(localId, requestId, confirmed)
        val nextLocalId = dao.insertPending(draft.copy(title = "Second"))
        assertEquals(localId, nextLocalId)
        assertNull(dao.acknowledgeCreate(localId, requestId, confirmed))
        assertEquals("Second", dao.getById(nextLocalId)!!.title)
    }
}
