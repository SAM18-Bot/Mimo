package com.mimo.app.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.POST
import retrofit2.http.Path

interface AccountApi {
    @PUT("/auth/me/gemini-key")
    suspend fun updatePersonalKey(@Body request: PersonalKeyRequest): Response<Void>

    @GET("/auth/google/client-id")
    suspend fun googleClientId(): GoogleClientId

    @POST("/auth/google")
    suspend fun googleLogin(@Body request: GoogleLogin): AuthResponse

    @POST("/parent/link")
    suspend fun linkStudent(@Body request: ParentLinkRequest): ParentLink

    @GET("/parent/children")
    suspend fun children(): List<UserOut>

    @GET("/parent/summary/{student}")
    suspend fun weeklySummary(@Path("student") student: Int): ParentSummary
}

data class PersonalKeyRequest(val api_key: String)
data class GoogleClientId(val client_id: String)
data class GoogleLogin(val token: String)
data class ParentLinkRequest(val code: String)
data class ParentLink(val parent_id: Int, val student_id: Int)
data class ParentSummary(
    val student_id: Int,
    val avg_focus_score: Double,
    val summaries: List<DailyHistoryItem>
)
