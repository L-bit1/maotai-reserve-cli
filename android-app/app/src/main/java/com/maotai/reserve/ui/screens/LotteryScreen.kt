package com.maotai.reserve.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.maotai.reserve.MaotaiApp
import com.maotai.reserve.data.LotteryItem
import com.maotai.reserve.data.requireOk
import com.maotai.reserve.ui.components.ErrorBanner
import com.maotai.reserve.ui.components.MaotaiHeroHeader
import com.maotai.reserve.ui.components.SectionTitle
import com.maotai.reserve.ui.components.StatusChip
import com.maotai.reserve.ui.theme.MaotaiRed
import com.maotai.reserve.ui.theme.SuccessGreen
import com.maotai.reserve.ui.theme.WarningOrange
import kotlinx.coroutines.launch

private const val IMAOTAI_PACKAGE = "com.moutai.mall"

@Composable
fun LotteryScreen(modifier: Modifier = Modifier) {
    val session = (LocalContext.current.applicationContext as MaotaiApp).session
    val context = LocalContext.current
    var pending by remember { mutableStateOf<List<LotteryItem>>(emptyList()) }
    var results by remember { mutableStateOf<List<LotteryItem>>(emptyList()) }
    var msg by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun load() {
        scope.launch {
            try {
                val p = session.call { it.pendingPayments() }
                p.requireOk()
                pending = p.data?.items ?: emptyList()
                val r = session.call { it.lotteryResults() }
                r.requireOk()
                results = r.data?.items ?: emptyList()
            } catch (e: Exception) {
                msg = session.unwrapApiError(e)
            }
        }
    }

    LaunchedEffect(Unit) { load() }

    Column(modifier.fillMaxSize()) {
        MaotaiHeroHeader("中签与付款", "待付款须在官方 i茅台 App 内完成")
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            msg?.let { ErrorBanner(message = it, onDismiss = { msg = null }) }
            Button(
                onClick = {
                    scope.launch {
                        try {
                            val res = session.call { it.syncLottery(true) }
                            res.requireOk()
                            msg = "已同步 ${res.data?.synced} 条"
                            load()
                        } catch (e: Exception) {
                            msg = session.unwrapApiError(e)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaotaiRed),
            ) { Text("同步中签结果") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = {
                        val intent = context.packageManager.getLaunchIntentForPackage(IMAOTAI_PACKAGE)
                        if (intent != null) context.startActivity(intent)
                        else context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.moutai.com.cn")))
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp),
                ) { Text("打开 i茅台") }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            try {
                                session.call { it.notifyPending() }.requireOk()
                                msg = "已尝试推送提醒"
                            } catch (e: Exception) {
                                msg = session.unwrapApiError(e)
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp),
                ) { Text("推送提醒") }
            }

            SectionTitle("待付款 ${pending.size} 笔")
            if (pending.isEmpty()) {
                Text(
                    "暂无待付款订单",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            pending.forEach { item ->
                Card(
                    Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = WarningOrange.copy(alpha = 0.08f)),
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text("${item.mobile}", fontWeight = FontWeight.Medium)
                            StatusChip("待付款", WarningOrange)
                        }
                        Text(item.itemName ?: "-", style = MaterialTheme.typography.bodySmall)
                        Text("订单: ${item.orderId ?: "-"}", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }

            SectionTitle("最近记录")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(results.take(30), key = { it.id }) { item ->
                    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(8.dp)) {
                        Row(
                            Modifier.padding(10.dp).fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Column {
                                Text("${item.mobile} ${item.itemName}")
                                Text(
                                    statusLabel(item.status) + " / " + payLabel(item.paymentStatus),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            if (item.status == "won") {
                                StatusChip("中签", SuccessGreen)
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun statusLabel(s: String?) = when (s) {
    "won" -> "中签"
    "failed" -> "未中"
    "waiting" -> "待公布"
    else -> s ?: "-"
}

private fun payLabel(s: String?) = when (s) {
    "pending" -> "待付款"
    "paid" -> "已付"
    else -> s ?: "-"
}
