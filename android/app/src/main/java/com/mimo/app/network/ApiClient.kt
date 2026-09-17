package com.mimo.app.network

import com.mimo.app.BuildConfig
import com.mimo.app.MimoApplication
import com.mimo.app.data.TokenManager
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private const val DEFAULT_BASE_URL = "https://mimo-e8u2.onrender.com/"

    @Volatile
    var baseUrl: String = DEFAULT_BASE_URL
        private set

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        redactHeader("Authorization")
    }

    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val context = runCatching { MimoApplication.instance }.getOrNull()
        val token = TokenManager.getToken(context)
        val request = if (!token.isNullOrBlank()) {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            original
        }
        chain.proceed(request)
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private fun createRetrofit(url: String): Retrofit = Retrofit.Builder()
        .baseUrl(url)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    @Volatile
    private var apiService: MimoApiService = createRetrofit(baseUrl).create(MimoApiService::class.java)

    val api: MimoApiService
        get() = apiService

    fun updateBaseUrl(newUrl: String) {
        val normalized = newUrl.trim().let { if (it.endsWith('/')) it else "$it/" }
        require(normalized.startsWith("https://") || normalized.startsWith("http://")) {
            "Server URL must start with http:// or https://"
        }
        synchronized(this) {
            if (normalized == baseUrl) return
            baseUrl = normalized
            apiService = createRetrofit(baseUrl).create(MimoApiService::class.java)
        }
    }
}
