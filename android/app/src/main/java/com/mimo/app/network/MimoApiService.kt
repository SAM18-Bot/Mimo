package com.mimo.app.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface MimoApiService {
    @POST("/auth/login")
    suspend fun login(@Body body: LoginRequest): AuthResponse

    @POST("/auth/register")
    suspend fun register(@Body body: RegisterRequest): AuthResponse

    @POST("/onboarding/complete")
    suspend fun completeOnboarding(@Body body: OnboardingRequest): UserOut

    @POST("/auth/google")
    suspend fun authenticateGoogle(@Body body: Map<String, String>): Map<String, Any>

    @GET("/reports/stats")
    suspend fun getStats(@Query("target_date") targetDate: String? = null): DailyStats

    @GET("/reports/history")
    suspend fun getHistory(@Query("days") days: Int = 7): List<DailyHistoryItem>

    @GET("/assignments/")
    suspend fun getAssignments(@Query("status") status: String? = null): List<Assignment>

    @POST("/assignments/")
    suspend fun createAssignment(@Body assignment: AssignmentCreate): Assignment

    @POST("/assignments/{id}/done")
    suspend fun markAssignmentDone(@Path("id") id: Int): Map<String, Any>

    @GET("/schedule/")
    suspend fun getSchedule(): List<ScheduleBlock>

    @GET("/schedule/today")
    suspend fun getScheduleToday(): List<ScheduleBlock>

    @GET("/screen/breakdown")
    suspend fun getScreenBreakdown(@Query("target_date") targetDate: String? = null): ScreenBreakdown

    @POST("/screen/mock")
    suspend fun syncMockScreen(@Body body: MockWindowEvent): Map<String, Any>

    @POST("/sync/push")
    suspend fun pushSync(@Body payload: SyncPayload): Map<String, Any>

    @GET("/sync/pull")
    suspend fun pullSync(): SyncPayload
}
