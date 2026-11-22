package com.mimo.app.network

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

class WebSocketManager {
    private val gson = Gson()
    private val client = OkHttpClient.Builder().followRedirects(false).build()
    private val handler = Handler(Looper.getMainLooper())
    private var webSocket: WebSocket? = null
    private var request: Request? = null
    private var reconnectAttempts = 0

    private val _events = MutableSharedFlow<WsEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<WsEvent> = _events

    private val _connectionState = MutableSharedFlow<ConnectionState>(replay = 1, extraBufferCapacity = 4)
    val connectionState: SharedFlow<ConnectionState> = _connectionState

    enum class ConnectionState { CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING }

    private val reconnect = Runnable {
        synchronized(this) { request?.let(::openSocket) }
    }

    @Synchronized
    fun connect(token: String? = null) {
        disconnect()
        if (token.isNullOrBlank()) return

        // OkHttp upgrades an HTTPS request to WSS itself.
        val url = ApiClient.baseUrl.toHttpUrl().newBuilder().encodedPath("/ws").build()
        val socketRequest = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $token")
            .build()
        request = socketRequest
        reconnectAttempts = 0
        openSocket(socketRequest)
    }

    private fun openSocket(socketRequest: Request) {
        _connectionState.tryEmit(ConnectionState.CONNECTING)
        webSocket = client.newWebSocket(socketRequest, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                synchronized(this@WebSocketManager) {
                    if (webSocket !== this@WebSocketManager.webSocket) return
                    reconnectAttempts = 0
                    _connectionState.tryEmit(ConnectionState.CONNECTED)
                }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                synchronized(this@WebSocketManager) {
                    if (webSocket !== this@WebSocketManager.webSocket) return
                    runCatching { gson.fromJson(text, WsEvent::class.java) }
                        .getOrNull()?.let { _events.tryEmit(it) }
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(code, null)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w("WebSocketManager", "WebSocket connection failed")
                socketEnded(webSocket, response?.code in setOf(401, 403))
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                socketEnded(webSocket, code == 1008)
            }
        })
    }

    @Synchronized
    private fun socketEnded(socket: WebSocket, denied: Boolean) {
        if (socket !== webSocket) return
        webSocket = null
        _connectionState.tryEmit(ConnectionState.DISCONNECTED)
        if (denied || reconnectAttempts >= 10) {
            request = null
        } else if (request != null) {
            reconnectAttempts++
            _connectionState.tryEmit(ConnectionState.RECONNECTING)
            handler.postDelayed(reconnect, minOf(reconnectAttempts * 2000L, 30000L))
        }
    }

    @Synchronized
    fun disconnect() {
        handler.removeCallbacks(reconnect)
        request = null
        val socket = webSocket
        webSocket = null
        socket?.cancel()
        _connectionState.tryEmit(ConnectionState.DISCONNECTED)
    }
}
