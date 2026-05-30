package com.maotai.reserve.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import com.maotai.reserve.BuildConfig
import com.maotai.reserve.data.ApiEnvelope
import com.maotai.reserve.data.SessionManager
import com.maotai.reserve.data.UpdateCheckData
import com.maotai.reserve.data.requireOk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

object AppUpdateHelper {
    val localVersionCode: Int get() = BuildConfig.VERSION_CODE
    val localVersionName: String get() = BuildConfig.VERSION_NAME

    suspend fun fetchUpdateInfo(session: SessionManager, baseUrl: String): UpdateCheckData? {
        val api = session.api(baseUrl, null)
        val res = api.checkUpdate(localVersionCode)
        res.requireOk()
        val data = res.data ?: return null
        return if (data.hasUpdate) data else null
    }

    suspend fun downloadApk(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit,
    ): File = withContext(Dispatchers.IO) {
        val dir = File(context.getExternalFilesDir("updates") ?: context.cacheDir, "apk").apply {
            mkdirs()
        }
        val out = File(dir, "maotai-reserve-update.apk")
        if (out.exists()) out.delete()

        val client = OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(300, TimeUnit.SECONDS)
            .build()
        val response = client.newCall(Request.Builder().url(url).build()).execute()
        if (!response.isSuccessful) {
            throw IllegalStateException("下载失败 HTTP ${response.code}")
        }
        val body = response.body ?: throw IllegalStateException("响应体为空")
        val total = body.contentLength()
        body.byteStream().use { input ->
            out.outputStream().use { output ->
                val buf = ByteArray(8192)
                var read: Int
                var done = 0L
                while (input.read(buf).also { read = it } != -1) {
                    output.write(buf, 0, read)
                    done += read
                    if (total > 0) {
                        onProgress((done * 100 / total).toInt().coerceIn(0, 100))
                    }
                }
            }
        }
        onProgress(100)
        out
    }

    fun canInstallPackages(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return true
        return context.packageManager.canRequestPackageInstalls()
    }

    fun openInstallPermissionSettings(context: Context) {
        val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
            data = Uri.parse("package:${context.packageName}")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    fun installApk(context: Context, apkFile: File) {
        if (!canInstallPackages(context)) {
            openInstallPermissionSettings(context)
            throw IllegalStateException("请先允许「安装未知应用」权限")
        }
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            apkFile,
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }
}
