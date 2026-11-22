package com.mimo.app.data

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

object TokenManager {
    private const val PREFS_NAME = "mimo_prefs"
    private const val LEGACY_TOKEN = "jwt_token"
    private const val ENCRYPTED_TOKEN = "encrypted_jwt"
    private const val KEY_ALIAS = "mimo_session"
    private const val IV_BYTES = 12

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    private val expired = kotlinx.coroutines.flow.MutableStateFlow(false)
    val sessionExpired: kotlinx.coroutines.flow.StateFlow<Boolean> = expired

    @Synchronized
    fun expireIfCurrent(context: Context, rejectedToken: String) {
        if (rejectedToken != cachedToken) return
        clearToken(context)
        expired.value = true
        context.stopService(android.content.Intent(context, com.mimo.app.service.RoastEnforcementService::class.java))
        context.stopService(android.content.Intent(context, com.mimo.app.tracker.MobileTrackerService::class.java))
    }

    private var cachedToken: String? = null
    private var isInitialized = false

    @Synchronized
    fun init(context: Context) {
        if (!isInitialized) {
            val prefs = getPrefs(context)
            val encrypted = prefs.getString(ENCRYPTED_TOKEN, null)
            cachedToken = encrypted?.let { runCatching { decrypt(it) }.getOrNull() }
            isInitialized = true
            prefs.getString(LEGACY_TOKEN, null)?.let { legacy ->
                saveToken(context, cachedToken ?: legacy)
            }
        }
    }

    @Synchronized
    fun saveToken(context: Context, token: String) {
        expired.value = false
        cachedToken = token
        isInitialized = true
        val encrypted = runCatching { encrypt(token) }.getOrNull()
        getPrefs(context).edit().remove(LEGACY_TOKEN).putString(ENCRYPTED_TOKEN, encrypted).apply()
    }

    @Synchronized
    fun getToken(context: Context? = null): String? {
        if (cachedToken == null && context != null) {
            init(context)
        }
        return cachedToken
    }

    @Synchronized
    fun clearToken(context: Context) {
        cachedToken = null
        getPrefs(context).edit().remove(ENCRYPTED_TOKEN).remove(LEGACY_TOKEN)
            .remove("onboarding_completed").apply()
    }

    private fun encryptionKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build()
            )
            generateKey()
        }
    }

    private fun encrypt(token: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, encryptionKey())
        check(cipher.iv.size == IV_BYTES)
        return Base64.encodeToString(cipher.iv + cipher.doFinal(token.toByteArray()), Base64.NO_WRAP)
    }

    private fun decrypt(token: String): String {
        val bytes = Base64.decode(token, Base64.NO_WRAP)
        require(bytes.size > IV_BYTES)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, encryptionKey(), GCMParameterSpec(128, bytes, 0, IV_BYTES))
        return cipher.doFinal(bytes, IV_BYTES, bytes.size - IV_BYTES).toString(Charsets.UTF_8)
    }

    fun role(context: Context): String? = runCatching {
        val claims = Base64.decode(getToken(context)!!.split('.')[1], Base64.URL_SAFE)
        org.json.JSONObject(claims.toString(Charsets.UTF_8)).getString("role")
    }.getOrNull()

    fun isStudent(context: Context) = role(context) == "student"

    fun isLoggedIn(context: Context): Boolean {
        return !getToken(context).isNullOrBlank()
    }

    fun setOnboardingCompleted(context: Context, completed: Boolean) {
        getPrefs(context).edit().putBoolean("onboarding_completed", completed).apply()
    }

    fun isOnboardingCompleted(context: Context): Boolean {
        return getPrefs(context).getBoolean("onboarding_completed", false)
    }
}
