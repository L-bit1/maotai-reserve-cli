package com.maotai.reserve.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.maotai.reserve.MaotaiApp
import com.maotai.reserve.data.JobItem
import com.maotai.reserve.data.QuickJobBody
import com.maotai.reserve.data.requireOk
import com.maotai.reserve.ui.components.ErrorBanner
import com.maotai.reserve.ui.components.MaotaiHeroHeader
import com.maotai.reserve.ui.components.SectionTitle
import com.maotai.reserve.ui.components.StatusChip
import com.maotai.reserve.ui.theme.MaotaiRed
import com.maotai.reserve.ui.theme.SuccessGreen
import com.maotai.reserve.ui.theme.WarningOrange
import kotlinx.coroutines.launch

@Composable
fun ReserveScreen(modifier: Modifier = Modifier) {
    val session = (androidx.compose.ui.platform.LocalContext.current.applicationContext as MaotaiApp).session
    var jobs by remember { mutableStateOf<List<JobItem>>(emptyList()) }
    var msg by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun load() {
        scope.launch {
            try {
                val res = session.call { it.jobs() }
                res.requireOk()
                jobs = res.data ?: emptyList()
            } catch (e: Exception) {
                msg = session.unwrapApiError(e)
            }
        }
    }

    LaunchedEffect(Unit) { load() }

    Column(modifier.fillMaxSize()) {
        MaotaiHeroHeader("预约任务", "立即执行或查看历史记录")
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            msg?.let { ErrorBanner(message = it, onDismiss = { msg = null }) }
            Button(
                onClick = {
                    scope.launch {
                        try {
                            val res = session.call { it.quickReserve(QuickJobBody(name = "每日自动预约")) }
                            res.requireOk()
                            msg = "任务 #${res.data?.jobId} 已启动"
                            load()
                        } catch (e: Exception) {
                            msg = session.unwrapApiError(e)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaotaiRed),
            ) { Text("立即执行每日预约") }
            OutlinedButton(
                onClick = {
                    scope.launch {
                        try {
                            val res = session.call { it.quickReserve(QuickJobBody(name = "试跑", dryRun = true)) }
                            res.requireOk()
                            msg = "试跑任务 #${res.data?.jobId} 已启动"
                            load()
                        } catch (e: Exception) {
                            msg = session.unwrapApiError(e)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
            ) { Text("试跑（不提交）") }

            SectionTitle("任务列表")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(jobs, key = { it.id }) { job ->
                    Card(
                        Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        elevation = CardDefaults.cardElevation(2.dp),
                    ) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(job.name, fontWeight = FontWeight.Medium)
                                StatusChip(
                                    text = jobStatusLabel(job.status),
                                    color = jobStatusColor(job.status),
                                )
                            }
                            if (job.status == "running") {
                                LinearProgressIndicator(
                                    progress = { job.progress / 100f },
                                    modifier = Modifier.fillMaxWidth(),
                                    color = MaotaiRed,
                                )
                            }
                            job.logPreview?.let {
                                Text(
                                    it,
                                    maxLines = 3,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun jobStatusLabel(s: String) = when (s) {
    "running" -> "执行中"
    "success" -> "成功"
    "partial" -> "部分成功"
    "failed" -> "失败"
    else -> s
}

private fun jobStatusColor(s: String) = when (s) {
    "success" -> SuccessGreen
    "running" -> WarningOrange
    "failed" -> MaotaiRed
    else -> MaotaiRed
}
