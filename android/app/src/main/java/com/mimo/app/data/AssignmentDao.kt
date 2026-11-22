package com.mimo.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface AssignmentDao {
    @Query("SELECT * FROM assignments ORDER BY due_date, due_time IS NULL, due_time, id DESC")
    fun getAllAssignments(): Flow<List<AssignmentEntity>>

    @Query("SELECT * FROM assignments WHERE is_synced = 0")
    suspend fun getUnsynced(): List<AssignmentEntity>

    @Query("SELECT * FROM assignments WHERE id = :id LIMIT 1")
    suspend fun getById(id: Int): AssignmentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRaw(assignment: AssignmentEntity): Long

    @Transaction
    suspend fun insert(assignment: AssignmentEntity): Long {
        if (assignment.id != 0) {
            val existing = getById(assignment.id)
            if (existing != null && !existing.isSynced && assignment.isSynced) {
                // Local assignment has unsynced changes; preserve it.
                return existing.id.toLong()
            }
        }
        return insertRaw(assignment)
    }

    @Query("SELECT COALESCE(MIN(id), 0) FROM assignments WHERE id < 0")
    suspend fun earliestLocalId(): Int

    @Query("DELETE FROM assignments WHERE id = :id")
    suspend fun deleteById(id: Int)

    @Transaction
    suspend fun insertPending(assignment: AssignmentEntity): Int {
        val id = earliestLocalId() - 1
        insertRaw(assignment.copy(id = id, requestId = java.util.UUID.randomUUID().toString()))
        return id
    }

    @Transaction
    suspend fun acknowledgeCreate(localId: Int, requestId: String, remote: AssignmentEntity): AssignmentEntity? {
        val current = getById(localId) ?: return null
        if (current.requestId != requestId) return null
        deleteById(localId)
        // The student may have marked the pending row done while the request was in flight.
        val needsDone = current.status == "done" && remote.status != "done"
        insert(if (needsDone) remote.copy(status = "done", isSynced = false) else remote)
        return getById(remote.id)
    }

    @Query("SELECT id FROM assignments WHERE is_synced = 1")
    suspend fun syncedIds(): List<Int>

    @Query("DELETE FROM assignments WHERE is_synced = 1 AND id IN (:ids)")
    suspend fun deleteSynced(ids: List<Int>)

    @Transaction
    suspend fun applyFullList(knownIds: List<Int>, assignments: List<AssignmentEntity>) {
        val remoteIds = assignments.mapTo(mutableSetOf()) { it.id }
        (knownIds - remoteIds).chunked(500).forEach { deleteSynced(it) }
        insertAll(assignments)
    }

    @Transaction
    suspend fun insertAll(assignments: List<AssignmentEntity>) {
        for (assignment in assignments) {
            insert(assignment)
        }
    }

    @Update
    suspend fun update(assignment: AssignmentEntity): Int

    @Delete
    suspend fun delete(assignment: AssignmentEntity)

    @Query("UPDATE assignments SET status = 'done', is_synced = 0 WHERE id = :id")
    suspend fun markDone(id: Int)

    @Query("UPDATE assignments SET is_synced = 1 WHERE id IN (:ids)")
    suspend fun markSynced(ids: List<Int>)
}
