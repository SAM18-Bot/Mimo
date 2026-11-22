package com.mimo.app.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class Advice(val recommendation: String = "", val priority: String = "")
data class StudySlot(val subject: String = "", val start_time: String = "", val end_time: String = "")
data class StudyReport(
    val recommendations: List<Advice> = emptyList(),
    val suggested_subjects: List<String> = emptyList(),
    val daily_study_plan: List<StudySlot> = emptyList(),
    val weekly_patterns: List<String> = emptyList()
)
data class SavedReport(val date: String? = null, val report: Map<String, String>? = null)
data class Questions(val questions: List<String> = emptyList())
data class AccountabilityEntry(val question: String, val answer: String)

interface CoachApi {
    @GET("study/recommendations")
    suspend fun recommendations(): StudyReport

    @GET("reports/eod/latest")
    suspend fun latest(): SavedReport

    @POST("reports/eod?wait=true")
    suspend fun generate(): SavedReport

    @GET("reports/accountability/questions")
    suspend fun questions(): Questions

    @GET("reports/accountability/today")
    suspend fun answers(): List<AccountabilityEntry>

    @POST("reports/accountability")
    suspend fun answer(@Body entry: AccountabilityEntry): Map<String, Boolean>
}
