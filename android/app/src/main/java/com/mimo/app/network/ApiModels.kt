package com.mimo.app.network

// POST /auth/login request
data class LoginRequest(
    val email: String,
    val password: String
)

// POST /auth/register request
data class RegisterRequest(
    val email: String,
    val password: String,
    val role: String = "student",
    val display_name: String? = null
)

// User info output
data class UserOut(
    val id: Int = 0,
    val email: String = "",
    val role: String = "student",
    val display_name: String? = null,
    val onboarding_completed: Boolean = false
)

// Auth response from login / register
data class AuthResponse(
    val access_token: String = "",
    val token_type: String = "bearer",
    val user: UserOut = UserOut()
)

// GET /schedule/ or /schedule/today
data class ScheduleBlock(
    val id: Int = 0,
    val day_of_week: Int = 0,
    val block_date: String? = null,
    val start_time: String = "",
    val end_time: String = "",
    val kind: String = "study",
    val title: String = "",
    val subject: String? = null,
    val flexibility: String = "flexible",
    val source: String = "user",
    val priority: String = "medium",
    val status: String = "planned"
)

// POST /screen/mock
data class MockWindowEvent(
    val app: String,
    val title: String = "",
    val category: String = ""
)

// GET /reports/stats
data class DailyStats(
    val date: String = "",
    val productive_s: Int = 0,
    val productive_min: Int = 0,
    val distracting_s: Int = 0,
    val distracting_min: Int = 0,
    val neutral_s: Int = 0,
    val neutral_min: Int = 0,
    val desk_time_min: Int = 0,
    val productive_apps: String = "none",
    val distracting_apps: String = "none",
    val focus_score: Double = 0.0,
    val letter_grade: String = "F",
    val score_verdict: String = "",
    val distraction_count: Int = 0,
    val absent_count: Int = 0,
    val longest_focus_min: Int = 0,
    val peak_hour: Int? = null,
    val due_today: List<String> = emptyList(),
    val submitted_today: List<String> = emptyList(),
    val overdue_list: List<String> = emptyList(),
    val upcoming_list: List<String> = emptyList()
)

// GET /reports/history - array items
data class DailyHistoryItem(
    val date: String = "",
    val focus_score: Double = 0.0,
    val productive_min: Int = 0,
    val distracting_min: Int = 0,
    val assignments_done: Int = 0,
    val assignments_due: Int = 0
)

// GET /assignments/
data class Assignment(
    val id: Int = 0,
    val title: String = "",
    val subject: String? = null,
    val due_date: String = "",
    val priority: String = "medium",
    val status: String = "pending",
    val notes: String? = null
)

// POST /assignments/ request
data class AssignmentCreate(
    val title: String,
    val subject: String? = null,
    val due_date: String,
    val priority: String = "medium",
    val notes: String? = null
)

// GET /screen/breakdown
data class ScreenBreakdown(
    val productive_min: Int = 0,
    val distracting_min: Int = 0,
    val neutral_min: Int = 0,
    val total_min: Int = 0,
    val top_productive: List<AppMinutes> = emptyList(),
    val top_distracting: List<AppMinutes> = emptyList()
)

data class AppMinutes(
    val app: String = "",
    val minutes: Int = 0
)

// WebSocket events
data class WsEvent(
    val type: String = "",
    val message: String? = null,
    val trigger: String? = null,
    val app: String? = null,
    val ts: String? = null,
    val stats: DailyStats? = null,
    val tasks: List<Assignment>? = null
)

// Sync Payload
data class SyncPayload(
    val date: String,
    val mobileProductiveMin: Int,
    val mobileDistractingMin: Int,
    val mobileNeutralMin: Int,
    val assignments: List<Assignment> = emptyList(),
    val mergedStats: DailyStats? = null
)
