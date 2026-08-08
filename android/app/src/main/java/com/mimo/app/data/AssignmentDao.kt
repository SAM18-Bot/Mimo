package com.mimo.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface AssignmentDao {
    @Query("SELECT * FROM assignments ORDER BY due_date ASC, id DESC")
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
