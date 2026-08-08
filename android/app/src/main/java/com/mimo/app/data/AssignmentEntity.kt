package com.mimo.app.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mimo.app.network.Assignment

@Entity(tableName = "assignments")
data class AssignmentEntity(
    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "id")
    val id: Int = 0,

    @ColumnInfo(name = "title")
    val title: String,

    @ColumnInfo(name = "subject")
    val subject: String? = null,

    @ColumnInfo(name = "due_date")
    val dueDate: String,

    @ColumnInfo(name = "priority")
    val priority: String = "medium",

    @ColumnInfo(name = "status")
    val status: String = "pending",

    @ColumnInfo(name = "notes")
    val notes: String? = null,

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false
)

fun AssignmentEntity.toDomain(): Assignment {
    return Assignment(
        id = id,
        title = title,
        subject = subject,
        due_date = dueDate,
        priority = priority,
        status = status,
        notes = notes
    )
}

fun Assignment.toEntity(isSynced: Boolean = false): AssignmentEntity {
    return AssignmentEntity(
        id = id,
        title = title,
        subject = subject,
        dueDate = due_date,
        priority = priority,
        status = status,
        notes = notes,
        isSynced = isSynced
    )
}
