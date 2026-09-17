package com.mimo.app.network

import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import okhttp3.*
import okhttp3.HttpUrl.Companion.toHttpUrl

class WebSocketManager {
    companion object {
        private const val TAG = "WebSocketManager"
    }

    private val gson = Gson()
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()

    private val _events = MutableSharedFlow<WsEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<WsEvent> = _events

    private val _connectionState = MutableSharedFlow<ConnectionState>(replay = 1, extraBufferCapacity = 4)
    val connectionState: SharedFlow<ConnectionState> = _connectionState

    enum class ConnectionState { CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING }

    private var shouldReconnect = true
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 10
    private var reconnectScheduled = false
    private var authToken: String? = null

    fun connect(token: String? = null) {
        shouldReconnect = false
        webSocket?.cancel()
        authToken = token
        shouldReconnect = true
        reconnectAttempts = 0
        doConnect()
    }

    private fun websocketUrl(): String {
        val httpUrl = ApiClient.baseUrl.toHttpUrl()
        val builder = httpUrl.newBuilder()
            .scheme(if (httpUrl.isHttps) "wss" else "ws")
            .encodedPath("/ws")
            .query(null)
        authToken?.takeIf { it.isNotBlank() }?.let { builder.addQueryParameter("token", it) }
        return builder.build().toString()
    }

    private fun doConnect() {
        _connectionState.tryEmit(ConnectionState.CONNECTING)
        val request = Request.Builder().url(websocketUrl()).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
                _connectionState.tryEmit(ConnectionState.CONNECTED)
                reconnectAttempts = 0
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val event = gson.fromJson(text, WsEvent::class.java)
                    _events.tryEmit(event)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse WS message: $text", e)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure", t)
                _connectionState.tryEmit(ConnectionState.DISCONNECTED)
                attemptReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed: $code $reason")
                _connectionState.tryEmit(ConnectionState.DISCONNECTED)
                attemptReconnect()
            }
        })
    }

    private fun attemptReconnect() {
        synchronized(this) {
            if (!shouldReconnect || reconnectScheduled || reconnectAttempts >= maxReconnectAttempts) return
            reconnectAttempts++
            reconnectScheduled = true
        }
        _connectionState.tryEmit(ConnectionState.RECONNECTING)
        Thread {
            Thread.sleep(minOf(reconnectAttempts * 2000L, 30000L))
            synchronized(this@WebSocketManager) {
                reconnectScheduled = false
            }
            if (shouldReconnect) doConnect()
        }.start()
    }

    fun disconnect() {
        shouldReconnect = false
        reconnectScheduled = false
        webSocket?.close(1000, "Client disconnect")
        webSocket = null
        _connectionState.tryEmit(ConnectionState.DISCONNECTED)
    }
}
