package com.mimo.app.network

import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AccountApiTest {
    @Test
    fun savingAPersonalKeyAcceptsAnEmptySuccessResponse() = runBlocking {
        val client = OkHttpClient.Builder().addInterceptor { chain ->
            Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1)
                .code(204).message("No Content").body(ByteArray(0).toResponseBody()).build()
        }.build()
        val account = Retrofit.Builder().baseUrl("https://example.invalid/")
            .client(client).addConverterFactory(GsonConverterFactory.create()).build()
            .create(AccountApi::class.java)
        assertTrue(account.updatePersonalKey(PersonalKeyRequest("test-only")).isSuccessful)
    }
}
