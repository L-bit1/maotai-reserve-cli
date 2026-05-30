package com.maotai.reserve.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.maotai.reserve.BuildConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

private val Context.dataStore by preferencesDataStore("maotai_session")

class SessionExpiredException(message: String = "登录已过期，请重新登录") : Exception(message)

class SessionManager(private val context: Context) {
    private val keyToken = stringPreferencesKey("token")
    private val keyBaseUrl = stringPreferencesKey("base_url")
    private val gson = Gson()
    private val onUnauthorized = AtomicReference<(() -> Unit)?>(null)

    val tokenFlow: Flow<String?> = context.dataStore.data.map { it[keyToken] }
    val baseUrlFlow: Flow<String> = context.dataStore.data.map {
        it[keyBaseUrl] ?: BuildConfig.DEFAULT_API_BASE
    }

    fun setOnUnauthorizedListener(listener: (() -> Unit)?) {
        onUnauthorized.set(listener)
    }

    suspend fun saveToken(token: String) {
        context.dataStore.edit { it[keyToken] = token }
    }

    suspend fun clearToken() {
        context.dataStore.edit { it.remove(keyToken) }
    }

    suspend fun saveBaseUrl(url: String) {
        val normalized = normalizeBaseUrl(url)
        context.dataStore.edit { it[keyBaseUrl] = normalized }
    }

    fun tokenBlocking(): String? = runBlocking { tokenFlow.first() }

    fun baseUrlBlocking(): String = runBlocking { baseUrlFlow.first() }

    fun normalizeBaseUrl(url: String): String {
        var u = url.trim()
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "http://$u"
        }
        return if (u.endsWith("/")) u else "$u/"
    }

    fun api(): ApiService = retrofit(baseUrlBlocking(), tokenBlocking()).create(ApiService::class.java)

    fun api(baseUrl: String, token: String?): ApiService =
        retrofit(normalizeBaseUrl(baseUrl), token).create(ApiService::class.java)

    private fun retrofit(baseUrl: String, token: String?): Retrofit {
        val auth = Interceptor { chain ->
            val req = if (!token.isNullOrBlank()) {
                chain.request().newBuilder()
                    .addHeader("Authorization", "Bearer $token")
                    .build()
            } else {
                chain.request()
            }
            chain.proceed(req)
        }
        val unauthorized = Interceptor { chain ->
            val response = chain.proceed(chain.request())
            if (response.code == 401) {
                val path = chain.request().url.encodedPath
                if (!path.contains("/auth/login") && !path.contains("/app/check-update")) {
                    runBlocking { clearToken() }
                    onUnauthorized.get()?.invoke()
                }
            }
            response
        }
        val log = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(auth)
            .addInterceptor(unauthorized)
            .addInterceptor(log)
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .build()
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    suspend fun <T> call(block: suspend (ApiService) -> T): T {
        val service = api()
        return try {
            block(service)
        } catch (e: HttpException) {
            if (e.code() == 401) {
                clearToken()
                onUnauthorized.get()?.invoke()
                throw SessionExpiredException()
            }
            throw e
        }
    }

    suspend fun validateSession(): Boolean {
        val token = tokenFlow.first()
        if (token.isNullOrBlank()) return false
        return try {
            val res = api().me()
            res.code == 0
        } catch (_: HttpException) {
            clearToken()
            false
        } catch (_: Exception) {
            true
        }
    }

    fun unwrapApiError(e: Exception): String {
        if (e is SessionExpiredException) return e.message ?: "登录已过期，请重新登录"
        if (e is HttpException) {
            val bodyMsg = parseErrorBody(e)
            return when (e.code()) {
                401 -> bodyMsg ?: "登录已过期，请重新登录"
                403 -> bodyMsg ?: "无权限访问"
                404 -> "接口不存在，请检查服务器地址是否以 /api/v1/ 结尾"
                429 -> bodyMsg ?: "请求过于频繁，请稍后再试"
                in 500..599 -> bodyMsg ?: "服务器错误(${e.code()})，请稍后重试"
                else -> bodyMsg ?: "请求失败 (${e.code()})"
            }
        }
        val msg = e.message.orEmpty()
        if (msg.contains("401")) return "登录已过期，请重新登录"
        if (msg.contains("Unable to resolve host")) return "无法连接服务器，请检查网络与地址"
        if (msg.contains("Failed to connect")) return "连接服务器失败，请确认地址与网络"
        return msg.ifBlank { "网络错误" }
    }

    private fun parseErrorBody(e: HttpException): String? {
        return try {
            val raw = e.response()?.errorBody()?.string() ?: return null
            val json = gson.fromJson(raw, JsonObject::class.java)
            json.get("message")?.asString?.takeIf { it.isNotBlank() }
        } catch (_: Exception) {
            null
        }
    }
}

fun ApiEnvelope<*>.requireOk() {
    if (code != 0) throw IllegalStateException(message.ifBlank { "请求失败($code)" })
}
