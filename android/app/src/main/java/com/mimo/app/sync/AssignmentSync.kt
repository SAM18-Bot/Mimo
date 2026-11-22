package com.mimo.app.sync

import com.mimo.app.data.AssignmentDao
import com.mimo.app.data.AssignmentEntity
import com.mimo.app.data.toEntity
import com.mimo.app.network.AssignmentCreate
import com.mimo.app.network.MimoApiService
import retrofit2.HttpException

internal suspend fun uploadAssignment(dao: AssignmentDao, api: MimoApiService, pending: AssignmentEntity) {
    val persisted = if (pending.id < 0) {
        val requestId = requireNotNull(pending.requestId)
        val created = api.createAssignment(AssignmentCreate(
            title = pending.title, subject = pending.subject, due_date = pending.dueDate,
            due_time = pending.dueTime, priority = pending.priority, notes = pending.notes,
            request_id = requestId,
        ))
        dao.acknowledgeCreate(pending.id, requestId, created.toEntity(isSynced = true)) ?: return
    } else pending

    if (!persisted.isSynced && persisted.status == "done") {
        try {
            api.markAssignmentDone(persisted.id)
            dao.markSynced(listOf(persisted.id))
        } catch (error: HttpException) {
            if (error.code() != 404) throw error
            dao.deleteById(persisted.id)
        }
    }
}
