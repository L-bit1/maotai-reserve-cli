package com.maotai.reserve.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.maotai.reserve.data.UpdateCheckData

@Composable
fun UpdateDialog(
    info: UpdateCheckData,
    downloading: Boolean,
    progress: Int,
    error: String?,
    onDismiss: () -> Unit,
    onDownload: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = { if (!info.forceUpdate && !downloading) onDismiss() },
        title = { Text("发现新版本 ${info.versionName}") },
        text = {
            Column {
                if (info.releaseNotes.isNotBlank()) {
                    Text(info.releaseNotes)
                    Spacer(Modifier.height(8.dp))
                } else {
                    Text("建议更新以获得最新功能与修复。")
                }
                if (downloading) {
                    Spacer(Modifier.height(12.dp))
                    LinearProgressIndicator(
                        progress = { progress / 100f },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text("下载中 $progress%")
                }
                error?.let {
                    Spacer(Modifier.height(8.dp))
                    Text(it, color = androidx.compose.material3.MaterialTheme.colorScheme.error)
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = onDownload,
                enabled = !downloading,
            ) { Text(if (downloading) "下载中…" else "立即更新") }
        },
        dismissButton = if (!info.forceUpdate) {
            {
                TextButton(
                    onClick = onDismiss,
                    enabled = !downloading,
                ) { Text("稍后") }
            }
        } else null,
    )
}
