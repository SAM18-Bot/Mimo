package com.mimo.app.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface MimoApiService {
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

    @GET("/screen/breakdown")
    suspend fun getScreenBreakdown(@Query("target_date") targetDate: String? = null): ScreenBreakdown

    @POST("/sync/push")
    suspend fun pushSync(@Body payload: SyncPayload): Map<String, Any>

    @GET("/sync/pull")
    suspend fun pullSync(): SyncPayload

    @POST("/auth/google")
    suspend fun authenticateGoogle(@Body body: Map<String, String>): Map<String, Any>
}
