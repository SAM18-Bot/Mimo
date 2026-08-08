package com.mimo.app.data

import com.mimo.app.network.Assignment
import com.mimo.app.network.DailyStats
import org.junit.Assert.*
import org.junit.Test

class DatabaseEntityTest {

    @Test
    fun assignmentEntity_toDomain_mapsAllFieldsCorrectly() {
        val entity = AssignmentEntity(
            id = 42,
            title = "Math HW 3",
            subject = "Mathematics",
            dueDate = "2026-08-10",
            priority = "high",
            status = "pending",
            notes = "Chapter 4 problems",
            isSynced = false
        )

        val domain = entity.toDomain()

        assertEquals(42, domain.id)
        assertEquals("Math HW 3", domain.title)
        assertEquals("Mathematics", domain.subject)
        assertEquals("2026-08-10", domain.due_date)
        assertEquals("high", domain.priority)
        assertEquals("pending", domain.status)
        assertEquals("Chapter 4 problems", domain.notes)
    }

    @Test
    fun assignmentDomain_toEntity_defaultsIsSyncedToFalse() {
        val domain = Assignment(
            id = 10,
            title = "Physics Lab",
            subject = "Physics",
            due_date = "2026-08-12",
            priority = "medium",
            status = "pending",
            notes = null
        )

        val entity = domain.toEntity()

        assertEquals(10, entity.id)
        assertEquals("Physics Lab", entity.title)
        assertEquals("Physics", entity.subject)
        assertEquals("2026-08-12", entity.dueDate)
        assertFalse(entity.isSynced)
    }

    @Test
    fun dailyStatsEntity_toDomain_calculatesDeskTimeAndMapsFields() {
        val entity = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 120,
            distractingMin = 30,
            neutralMin = 15,
            focusScore = 80.0,
            isSynced = false
        )

        val domain = entity.toDomain()

        assertEquals("2026-08-07", domain.date)
        assertEquals(120, domain.productive_min)
        assertEquals(30, domain.distracting_min)
        assertEquals(15, domain.neutral_min)
        assertEquals(165, domain.desk_time_min)
        assertEquals(80.0, domain.focus_score, 0.001)
    }

    @Test
    fun dailyStatsDomain_toEntity_preservesSyncedFlagWhenPassed() {
        val domain = DailyStats(
            date = "2026-08-07",
            productive_min = 90,
            distracting_min = 10,
            neutral_min = 5,
            focus_score = 90.0
        )

        val entitySynced = domain.toEntity(isSynced = true)
        val entityUnsynced = domain.toEntity(isSynced = false)

        assertTrue(entitySynced.isSynced)
        assertFalse(entityUnsynced.isSynced)
        assertEquals("2026-08-07", entitySynced.date)
        assertEquals(90, entitySynced.productiveMin)
    }

    @Test
    fun assignmentEntity_unsyncedFlag_preservesStateDuringRoundtrip() {
        val entityUnsynced = AssignmentEntity(
            id = 5,
            title = "Offline Edit Task",
            dueDate = "2026-08-15",
            status = "done",
            isSynced = false
        )
        val domain = entityUnsynced.toDomain()
        val convertedBackSynced = domain.toEntity(isSynced = true)
        val convertedBackUnsynced = domain.toEntity(isSynced = false)

        assertFalse(entityUnsynced.isSynced)
        assertTrue(convertedBackSynced.isSynced)
        assertFalse(convertedBackUnsynced.isSynced)
        assertEquals("done", convertedBackSynced.status)
    }
}
