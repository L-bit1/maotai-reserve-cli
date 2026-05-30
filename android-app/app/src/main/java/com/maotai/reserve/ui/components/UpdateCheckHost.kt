package com.maotai.reserve.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.maotai.reserve.data.SessionManager
import com.maotai.reserve.data.UpdateCheckData
import com.maotai.reserve.update.AppUpdateHelper
import kotlinx.coroutines.launch

/** 启动时检查服务器是否有新版本，有则弹窗下载安装。 */
@Composable
fun UpdateCheckHost(
    baseUrl: String,
    session: SessionManager,
    enabled: Boolean = true,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var updateInfo by remember { mutableStateOf<UpdateCheckData?>(null) }
    var downloading by remember { mutableStateOf(false) }
    var progress by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(baseUrl, enabled) {
        if (!enabled || baseUrl.isBlank()) return@LaunchedEffect
        try {
            val url = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
            updateInfo = AppUpdateHelper.fetchUpdateInfo(session, url)
        } catch (_: Exception) {
            // 网络不可达时静默，不阻断登录
        }
    }

    updateInfo?.let { info ->
        UpdateDialog(
            info = info,
            downloading = downloading,
            progress = progress,
            error = error,
            onDismiss = { updateInfo = null },
            onDownload = {
                scope.launch {
                    downloading = true
                    error = null
                    try {
                        val file = AppUpdateHelper.downloadApk(context, info.downloadUrl) { p ->
                            progress = p
                        }
                        AppUpdateHelper.installApk(context, file)
                    } catch (e: Exception) {
                        error = e.message ?: "更新失败"
                    } finally {
                        downloading = false
                    }
                }
            },
        )
    }
}
