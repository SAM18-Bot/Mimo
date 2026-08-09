package com.mimo.app.data

import android.content.Context
import android.content.SharedPreferences

object TokenManager {
    private const val PREFS_NAME = "mimo_prefs"
    private const val KEY_JWT_TOKEN = "jwt_token"

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    private var cachedToken: String? = null
    private var isInitialized = false

    fun init(context: Context) {
        if (!isInitialized) {
            cachedToken = getPrefs(context).getString(KEY_JWT_TOKEN, null)
            isInitialized = true
        }
    }

    fun saveToken(context: Context, token: String) {
        cachedToken = token
        getPrefs(context).edit().putString(KEY_JWT_TOKEN, token).apply()
    }

    fun getToken(context: Context? = null): String? {
        if (cachedToken == null && context != null) {
            init(context)
        }
        return cachedToken
    }

    fun clearToken(context: Context) {
        cachedToken = null
        getPrefs(context).edit().remove(KEY_JWT_TOKEN).apply()
    }

    fun isLoggedIn(context: Context): Boolean {
        return !getToken(context).isNullOrBlank()
    }
}
