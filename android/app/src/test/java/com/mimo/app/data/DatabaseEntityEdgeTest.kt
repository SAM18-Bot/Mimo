package com.mimo.app.data

import com.mimo.app.network.Assignment
import com.mimo.app.network.DailyStats
import org.junit.Assert.*
import org.junit.Test

class DatabaseEntityEdgeTest {

    @Test
    fun assignmentEntity_edgeCases_emptyStringsAndNulls() {
        val entity = AssignmentEntity(
            id = 0,
            title = "",
            subject = null,
            dueDate = "",
            priority = "",
            status = "",
            notes = null,
            isSynced = false
        )

        val domain = entity.toDomain()

        assertEquals(0, domain.id)
        assertEquals("", domain.title)
        assertNull(domain.subject)
        assertEquals("", domain.due_date)
        assertEquals("", domain.priority)
        assertEquals("", domain.status)
        assertNull(domain.notes)

        // Roundtrip mapping
        val entityRoundtrip = domain.toEntity(isSynced = true)
        assertEquals(0, entityRoundtrip.id)
        assertEquals("", entityRoundtrip.title)
        assertNull(entityRoundtrip.subject)
        assertEquals("", entityRoundtrip.dueDate)
        assertTrue(entityRoundtrip.isSynced)
    }

    @Test
    fun assignmentEntity_specialCharactersAndLongText() {
        val longText = "A".repeat(1000)
        val specialChars = "Math & Physics <script>alert(1)</script> ' \" \n\t \uD83D\uDE80"

        val entity = AssignmentEntity(
            id = 999999,
            title = specialChars,
            subject = longText,
            dueDate = "2026-12-31T23:59:59Z",
            priority = "high",
            status = "done",
            notes = specialChars,
            isSynced = true
        )

        val domain = entity.toDomain()
        assertEquals(specialChars, domain.title)
        assertEquals(longText, domain.subject)
        assertEquals(specialChars, domain.notes)
        assertTrue(entity.isSynced)
    }

    @Test
    fun dailyStatsEntity_zeroAndExtremeValues() {
        val entityZero = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 0,
            distractingMin = 0,
            neutralMin = 0,
            focusScore = 0.0,
            isSynced = false
        )

        val domainZero = entityZero.toDomain()
        assertEquals(0, domainZero.desk_time_min)
        assertEquals(0.0, domainZero.focus_score, 0.0001)

        val entityMax = DailyStatsEntity(
            date = "2026-08-07",
            productiveMin = 10000,
            distractingMin = 5000,
            neutralMin = 2000,
            focusScore = 66.6667,
            isSynced = true
        )

        val domainMax = entityMax.toDomain()
        assertEquals(17000, domainMax.desk_time_min)
        assertEquals(66.6667, domainMax.focus_score, 0.0001)
    }

    @Test
    fun dailyStats_bidirectionalMapping_preservesFields() {
        val domainOriginal = DailyStats(
            date = "2026-08-07",
            productive_min = 180,
            distracting_min = 45,
            neutral_min = 30,
            focus_score = 80.0
        )

        val entity = domainOriginal.toEntity(isSynced = false)
        assertFalse(entity.isSynced)
        assertEquals(180, entity.productiveMin)
        assertEquals(45, entity.distractingMin)
        assertEquals(30, entity.neutralMin)

        val domainRestored = entity.toDomain()
        assertEquals(domainOriginal.date, domainRestored.date)
        assertEquals(domainOriginal.productive_min, domainRestored.productive_min)
        assertEquals(domainOriginal.distracting_min, domainRestored.distracting_min)
        assertEquals(domainOriginal.neutral_min, domainRestored.neutral_min)
        assertEquals(255, domainRestored.desk_time_min)
    }
}
