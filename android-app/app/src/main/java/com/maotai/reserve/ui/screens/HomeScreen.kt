package com.maotai.reserve.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import com.maotai.reserve.data.DashboardData
import com.maotai.reserve.data.QuickJobBody
import com.maotai.reserve.data.SessionExpiredException
import com.maotai.reserve.data.requireOk
import com.maotai.reserve.ui.components.ActionRow
import com.maotai.reserve.ui.components.ErrorBanner
import com.maotai.reserve.ui.components.LoadingBlock
import com.maotai.reserve.ui.components.MaotaiHeroHeader
import com.maotai.reserve.ui.components.RefreshHintRow
import com.maotai.reserve.ui.components.SectionTitle
import com.maotai.reserve.ui.components.StatCard
import com.maotai.reserve.ui.components.StatusChip
import com.maotai.reserve.ui.theme.MaotaiRed
import com.maotai.reserve.ui.theme.SuccessGreen
import com.maotai.reserve.ui.theme.WarningOrange
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(
    onOpenAccounts: () -> Unit,
    onOpenLottery: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val session = (androidx.compose.ui.platform.LocalContext.current.applicationContext as MaotaiApp).session
    var dash by remember { mutableStateOf<DashboardData?>(null) }
    var loading by remember { mutableStateOf(true) }
    var msg by remember { mutableStateOf<String?>(null) }
    var reserving by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun refresh() {
        scope.launch {
            loading = true
            msg = null
            try {
                val res = session.call { it.dashboard() }
                res.requireOk()
                dash = res.data
            } catch (e: SessionExpiredException) {
                msg = e.message
            } catch (e: Exception) {
                msg = session.unwrapApiError(e)
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(Unit) { refresh() }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
    ) {
        MaotaiHeroHeader(
            title = "今日概览",
            subtitle = "服务器自动执行每日 9 点预约",
        )

        Column(
            Modifier.padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Spacer(Modifier.height(4.dp))
            RefreshHintRow(onRefresh = { refresh() })

            msg?.let { ErrorBanner(message = it, onDismiss = { msg = null }) }

            when {
                loading && dash == null -> LoadingBlock()
                dash != null -> {
                    val d = dash!!
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        StatCard(
                            label = "已登录",
                            value = "${d.accountsLoggedIn}/${d.accountsTotal}",
                            modifier = Modifier.weight(1f),
                            accent = SuccessGreen,
                        )
                        StatCard(
                            label = "启用账号",
                            value = "${d.accountsEnabled}",
                            modifier = Modifier.weight(1f),
                        )
                    }
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        StatCard(
                            label = "启用商品",
                            value = "${d.productsEnabled}",
                            modifier = Modifier.weight(1f),
                            accent = MaotaiRed,
                        )
                        StatCard(
                            label = "最近任务",
                            value = d.lastJob?.status ?: "无",
                            modifier = Modifier.weight(1f),
                            accent = if (d.lastJob?.status == "running") WarningOrange else MaotaiRed,
                        )
                    }

                    d.lastJob?.let { j ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                            ),
                        ) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("最近任务", fontWeight = FontWeight.Medium)
                                Text("${j.name} · ${j.progress}%")
                                StatusChip(
                                    text = jobStatusLabel(j.status),
                                    color = jobStatusColor(j.status),
                                )
                            }
                        }
                    }

                    d.scheduler?.jobs?.takeIf { it.isNotEmpty() }?.let { jobs ->
                        SectionTitle("服务器定时")
                        jobs.forEach { sj ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(10.dp),
                            ) {
                                Row(
                                    Modifier.padding(12.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                                ) {
                                    Text(schedulerLabel(sj.id), style = MaterialTheme.typography.bodyMedium)
                                    Text(
                                        formatNextRun(sj.nextRun),
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }
            }

            SectionTitle("快捷操作")

            Button(
                onClick = {
                    scope.launch {
                        reserving = true
                        msg = null
                        try {
                            val res = session.call { it.quickReserve(QuickJobBody()) }
                            res.requireOk()
                            msg = res.data?.message ?: "预约任务已启动"
                            refresh()
                        } catch (e: Exception) {
                            msg = session.unwrapApiError(e)
                        } finally {
                            reserving = false
                        }
                    }
                },
                enabled = !reserving,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaotaiRed),
            ) {
                Text(if (reserving) "启动中…" else "一键每日预约")
            }

            ActionRow(
                icon = Icons.Default.People,
                title = "管理 i茅台 账号",
                subtitle = "添加账号、短信登录、搜索",
                onClick = onOpenAccounts,
            )
            ActionRow(
                icon = Icons.Default.Star,
                title = "中签与待付款",
                subtitle = "同步结果、打开官方 App 付款",
                onClick = onOpenLottery,
            )

            Spacer(Modifier.height(8.dp))
            Text(
                "说明：预约在服务器执行；若提示登录过期，请重新输入管理密码。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(16.dp))
        }
    }
}

private fun jobStatusLabel(s: String) = when (s) {
    "running" -> "执行中"
    "success" -> "成功"
    "partial" -> "部分成功"
    "failed" -> "失败"
    "pending" -> "等待中"
    else -> s
}

private fun jobStatusColor(s: String) = when (s) {
    "success" -> SuccessGreen
    "running" -> WarningOrange
    "failed" -> MaotaiRed
    else -> MaotaiRed
}

private fun schedulerLabel(id: String) = when (id) {
    "daily_reserve" -> "每日申购"
    "lottery_sync" -> "中签同步"
    "token_check" -> "Token 巡检"
    "weekend_happy" -> "周末欢乐购"
    else -> id
}

private fun formatNextRun(iso: String?): String {
    if (iso.isNullOrBlank()) return "—"
    return iso.replace("T", " ").take(16)
}
