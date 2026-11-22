package com.mimo.app.network

import com.mimo.app.MimoApplication
import com.mimo.app.data.TokenManager
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.HttpUrl.Companion.toHttpUrl
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.IOException
import java.util.concurrent.TimeUnit

object ApiClient {
    private const val DEFAULT_BASE_URL = "https://mimo-e8u2.onrender.com/"

    @Volatile
    var baseUrl: String = DEFAULT_BASE_URL
        private set

    private fun currentToken(): String? {
        val context = runCatching { MimoApplication.instance }.getOrNull()
        return TokenManager.getToken(context)
    }

    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val context = runCatching { MimoApplication.instance }.getOrNull()
        val token = TokenManager.getToken(context)
        val server = baseUrl.toHttpUrl()
        val sameOrigin = original.url.host == server.host && original.url.port == server.port &&
            original.url.scheme == server.scheme
        if (!sameOrigin) throw IOException("The selected server changed")
        val response = chain.proceed(original)
        if (response.code == 401 && context != null && token != null &&
            original.header("Authorization") == "Bearer $token") {
            TokenManager.expireIfCurrent(context, token)
        }
        response
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .followRedirects(false)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .build()

    private var retrofit: Retrofit? = null
    private var serviceToken: String? = null

    @Synchronized
    fun <T> createService(service: Class<T>): T {
        val token = currentToken()
        val cached = retrofit
        if (cached != null && cached.baseUrl().toString() == baseUrl && token == serviceToken) {
            return cached.create(service)
        }
        // A call started by an old screen keeps its original account, including
        // when Android resumes a suspended coroutine after another sign-in.
        val bound = Retrofit.Builder()
            .baseUrl(baseUrl)
            .callFactory { request ->
                val authorized = if (token != null && request.header("Authorization") == null) {
                    request.newBuilder().header("Authorization", "Bearer $token").build()
                } else request
                okHttpClient.newCall(authorized)
            }
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        retrofit = bound
        serviceToken = token
        return bound.create(service)
    }

    val api: MimoApiService
        get() = createService(MimoApiService::class.java)

    fun normalizeOrigin(newUrl: String): String {
        val url = newUrl.trim().toHttpUrl()
        require(url.isHttps && url.encodedPath == "/" && url.query == null &&
            url.fragment == null && url.username.isEmpty() && url.password.isEmpty()) {
            "Server URL must be an HTTPS origin"
        }
        return url.toString()
    }

    fun restoreOrigin(context: android.content.Context) {
        val prefs = context.getSharedPreferences("mimo_connection", android.content.Context.MODE_PRIVATE)
        val stored = prefs.getString("server_origin", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
        val normalized = runCatching { normalizeOrigin(stored) }.getOrDefault(DEFAULT_BASE_URL)
        synchronized(this) {
            baseUrl = normalized
            retrofit = null
            serviceToken = null
        }
    }

    fun updateBaseUrl(newUrl: String) {
        val normalized = normalizeOrigin(newUrl)
        synchronized(this) {
            if (normalized == baseUrl) return
            runCatching { MimoApplication.instance }.getOrNull()?.let { context ->
                TokenManager.clearToken(context)
                context.getSharedPreferences("mimo_connection", android.content.Context.MODE_PRIVATE)
                    .edit().putString("server_origin", normalized).apply()
            }
            baseUrl = normalized
            retrofit = null
            serviceToken = null
        }
    }
}
