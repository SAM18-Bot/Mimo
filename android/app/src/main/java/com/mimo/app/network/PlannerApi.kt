package com.mimo.app.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class PlannerSubject(val name: String = "", val priority: String = "medium")
data class PlannerActivity(
    val title: String = "",
    val day_of_week: Int = 0,
    val start_time: String = "17:00",
    val end_time: String = "18:00",
)

data class PlannerProfile(
    val wake_time: String,
    val sleep_time: String,
    val timezone: String,
    val school_start: String?,
    val school_end: String?,
    val study_goal_minutes: Int,
    val session_minutes: Int,
    val break_minutes: Int,
    val notes: String?,
)

data class PlannerRequest(
    val wake_time: String,
    val sleep_time: String,
    val timezone: String,
    val school_days: List<Int>,
    val school_start: String?,
    val school_end: String?,
    val study_goal_minutes: Int,
    val session_minutes: Int,
    val break_minutes: Int,
    val subjects: List<PlannerSubject>,
    val fixed_blocks: List<PlannerActivity>,
    val notes: String?,
)

data class BuiltPlan(val profile: PlannerProfile, val blocks: List<ScheduleBlock>)
data class BlockStatus(val status: String)
data class ScheduleSuggestion(val message: String)
data class ScheduleSuggestions(val suggestions: List<ScheduleSuggestion>)
data class AssignmentCommand(val text: String, val due_time: String?)

interface PlannerApi {
    @GET("schedule/profile")
    suspend fun profile(): Response<PlannerProfile>

    @GET("schedule/weekly")
    suspend fun week(): List<ScheduleBlock>

    @POST("schedule/onboarding")
    suspend fun build(@Body request: PlannerRequest): BuiltPlan

    @PATCH("schedule/blocks/{id}")
    suspend fun setStatus(@Path("id") id: Int, @Body status: BlockStatus): ScheduleBlock

    @POST("schedule/reschedule")
    suspend fun reschedule(@Query("target_date") date: String): List<ScheduleBlock>

    @POST("schedule/boost")
    suspend fun boost(@Query("target_date") date: String): List<ScheduleBlock>

    @GET("schedule/smart-suggestions")
    suspend fun suggestions(@Query("target_date") date: String): ScheduleSuggestions

    @POST("assignments/nlp")
    suspend fun quickAdd(@Body command: AssignmentCommand): Assignment
}
