package com.mimo.app.ui.planner

import com.mimo.app.network.*
import java.time.ZoneId

data class ScheduleDraft(
    val wake: String = "06:30",
    val sleep: String = "22:30",
    val timezone: String = ZoneId.systemDefault().id,
    val goalMinutes: String = "120",
    val sessionMinutes: String = "50",
    val breakMinutes: String = "10",
    val schoolDays: Set<Int> = (0..4).toSet(),
    val schoolStart: String = "08:00",
    val schoolEnd: String = "15:00",
    val subjects: List<PlannerSubject> = emptyList(),
    val activities: List<PlannerActivity> = emptyList(),
    val year: String = "",
    val primaryGoal: String = "",
    val notes: String = "",
) {
    fun validationError(): String? = when {
        (listOf(wake, sleep) + (if (schoolDays.isEmpty()) emptyList() else listOf(schoolStart, schoolEnd)) +
            activities.flatMap { listOf(it.start_time, it.end_time) }).any { !it.matches(Regex("(?:[01][0-9]|2[0-3]):[0-5][0-9]")) } ->
                "Use a 24-hour time such as 08:30."
        runCatching { ZoneId.of(timezone) }.isFailure -> "Enter a time zone such as Asia/Kolkata."
        wake == sleep -> "Choose different wake and sleep times."
        goalMinutes.toIntOrNull() !in 1..600 -> "Study goal must be between 1 and 600 minutes."
        sessionMinutes.toIntOrNull() !in 15..180 -> "Session length must be between 15 and 180 minutes."
        breakMinutes.toIntOrNull() !in 0..60 -> "Break length must be between 0 and 60 minutes."
        schoolDays.isNotEmpty() && schoolStart >= schoolEnd -> "School must end after it starts."
        subjects.any { it.name.isBlank() || it.name.trim().length > 100 } -> "Enter a subject name of up to 100 characters."
        activities.any { it.title.isBlank() || it.title.trim().length > 200 } -> "Enter an activity title of up to 200 characters."
        activities.any { it.start_time >= it.end_time } -> "Each activity must end after it starts."
        else -> null
    }

    fun request(): PlannerRequest {
        require(validationError() == null)
        val context = listOfNotNull(
            year.trim().takeIf { it.isNotEmpty() }?.let { "Year of Study: $it" },
            primaryGoal.trim().takeIf { it.isNotEmpty() }?.let { "Primary Goal: $it" },
            notes.trim().takeIf { it.isNotEmpty() },
        ).joinToString("\n")
        return PlannerRequest(
            wake, sleep, timezone, schoolDays.sorted(),
            schoolStart.takeIf { schoolDays.isNotEmpty() }, schoolEnd.takeIf { schoolDays.isNotEmpty() },
            goalMinutes.toInt(), sessionMinutes.toInt(), breakMinutes.toInt(),
            subjects.map { it.copy(name = it.name.trim()) },
            activities.map { it.copy(title = it.title.trim()) }, context.ifBlank { null },
        )
    }

    fun withSubject(subject: String?): ScheduleDraft {
        val name = subject?.trim().orEmpty()
        if (name.isEmpty() || subjects.any { it.name.equals(name, ignoreCase = true) }) return this
        return copy(subjects = subjects + PlannerSubject(name))
    }

    companion object {
        fun from(profile: PlannerProfile?, blocks: List<ScheduleBlock>): ScheduleDraft {
            if (profile == null) return ScheduleDraft()
            val recurring = blocks.filter { it.block_date == null }
            val lines = profile.notes.orEmpty().lines()
            fun extract(label: String) = lines.firstOrNull { it.startsWith(label) }?.removePrefix(label)?.trim().orEmpty()
            return ScheduleDraft(
                wake = profile.wake_time, sleep = profile.sleep_time,
                timezone = profile.timezone.takeUnless { it == "local" } ?: ZoneId.systemDefault().id,
                goalMinutes = profile.study_goal_minutes.toString(), sessionMinutes = profile.session_minutes.toString(),
                breakMinutes = profile.break_minutes.toString(),
                schoolDays = recurring.filter { it.kind == "school" }.map { it.day_of_week }.toSet(),
                schoolStart = profile.school_start ?: "08:00", schoolEnd = profile.school_end ?: "15:00",
                subjects = recurring.filter { it.kind == "study" }.mapNotNull { b ->
                    b.subject?.let { PlannerSubject(it, b.priority) }
                }.distinctBy { it.name.lowercase() },
                activities = recurring.filter { it.kind == "fixed" }.map {
                    PlannerActivity(it.title, it.day_of_week, it.start_time, it.end_time)
                },
                year = extract("Year of Study:"), primaryGoal = extract("Primary Goal:"),
                notes = lines.filterNot { it.startsWith("Year of Study:") || it.startsWith("Primary Goal:") }.joinToString("\n"),
            )
        }
    }
}
