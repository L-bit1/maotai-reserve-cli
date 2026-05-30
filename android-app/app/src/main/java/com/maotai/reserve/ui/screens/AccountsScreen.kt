package com.maotai.reserve.ui.screens

import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.maotai.reserve.MaotaiApp
import com.maotai.reserve.data.AccountCreateBody
import com.maotai.reserve.data.AccountItem
import com.maotai.reserve.data.AccountUpdateBody
import com.maotai.reserve.data.VcodeLoginBody
import com.maotai.reserve.data.requireOk
import com.maotai.reserve.ui.components.ErrorBanner
import com.maotai.reserve.ui.components.MaotaiHeroHeader
import com.maotai.reserve.ui.components.StatusChip
import com.maotai.reserve.ui.theme.MaotaiRed
import com.maotai.reserve.ui.theme.SuccessGreen
import com.maotai.reserve.ui.theme.WarningOrange
import kotlinx.coroutines.launch

@Composable
fun AccountsScreen(modifier: Modifier = Modifier) {
    val session = (androidx.compose.ui.platform.LocalContext.current.applicationContext as MaotaiApp).session
    var list by remember { mutableStateOf<List<AccountItem>>(emptyList()) }
    var total by remember { mutableStateOf(0) }
    var showAdd by remember { mutableStateOf(false) }
    var editAcc by remember { mutableStateOf<AccountItem?>(null) }
    var loginAcc by remember { mutableStateOf<AccountItem?>(null) }
    var vcode by remember { mutableStateOf("") }
    var msg by remember { mutableStateOf<String?>(null) }
    var search by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    fun load() {
        scope.launch {
            try {
                val q = search.trim().ifEmpty { null }
                val res = session.call { it.accounts(search = q) }
                res.requireOk()
                list = res.data?.items ?: emptyList()
                total = res.data?.total ?: list.size
            } catch (e: Exception) {
                msg = session.unwrapApiError(e)
            }
        }
    }

    LaunchedEffect(Unit) { load() }

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAdd = true },
                containerColor = MaotaiRed,
            ) {
                Icon(Icons.Default.Add, contentDescription = "添加", tint = androidx.compose.ui.graphics.Color.White)
            }
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            MaotaiHeroHeader("i茅台 账号", "共 $total 个 · 点击卡片编辑")
            Column(Modifier.padding(horizontal = 16.dp)) {
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = search,
                    onValueChange = { search = it },
                    label = { Text("搜索手机号 / 城市") },
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = MaotaiRed),
                )
                TextButton(onClick = { load() }, modifier = Modifier.align(Alignment.End)) {
                    Text("搜索 / 刷新", color = MaotaiRed)
                }
                msg?.let { ErrorBanner(message = it, onDismiss = { msg = null }) }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(list, key = { it.id }) { acc ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { editAcc = acc },
                            shape = RoundedCornerShape(12.dp),
                            elevation = CardDefaults.cardElevation(2.dp),
                        ) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    Text(acc.mobile, fontWeight = FontWeight.SemiBold)
                                    StatusChip(
                                        text = if (acc.hasToken) "已登录" else "未登录",
                                        color = if (acc.hasToken) SuccessGreen else WarningOrange,
                                    )
                                }
                                Text(
                                    "${acc.province ?: ""} ${acc.city ?: ""} · ${acc.shopStrategy ?: "-"}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    TextButton(onClick = {
                                        scope.launch {
                                            try {
                                                session.call { it.sendVcode(acc.id) }.requireOk()
                                                loginAcc = acc
                                                msg = "验证码已发送"
                                            } catch (e: Exception) {
                                                msg = session.unwrapApiError(e)
                                            }
                                        }
                                    }) { Text("发码", color = MaotaiRed) }
                                    TextButton(onClick = { loginAcc = acc }) { Text("登录", color = MaotaiRed) }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showAdd) AddAccountDialog(
        onDismiss = { showAdd = false },
        onSave = { body ->
            scope.launch {
                try {
                    session.call { it.createAccount(body) }.requireOk()
                    showAdd = false
                    load()
                } catch (e: Exception) {
                    msg = session.unwrapApiError(e)
                }
            }
        },
    )

    editAcc?.let { acc ->
        EditAccountDialog(
            acc = acc,
            onDismiss = { editAcc = null },
            onSave = { body ->
                scope.launch {
                    try {
                        session.call { it.updateAccount(acc.id, body) }.requireOk()
                        editAcc = null
                        load()
                    } catch (e: Exception) {
                        msg = session.unwrapApiError(e)
                    }
                }
            },
        )
    }

    loginAcc?.let { acc ->
        AlertDialog(
            onDismissRequest = { loginAcc = null },
            title = { Text("短信登录 ${acc.mobile}") },
            text = {
                OutlinedTextField(
                    value = vcode,
                    onValueChange = { vcode = it },
                    label = { Text("验证码") },
                    singleLine = true,
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        try {
                            session.call { it.loginAccount(acc.id, VcodeLoginBody(vcode.trim())) }.requireOk()
                            loginAcc = null
                            vcode = ""
                            load()
                            msg = "登录成功"
                        } catch (e: Exception) {
                            msg = session.unwrapApiError(e)
                        }
                    }
                }) { Text("确认", color = MaotaiRed) }
            },
            dismissButton = {
                TextButton(onClick = { loginAcc = null }) { Text("取消") }
            },
        )
    }
}

@Composable
private fun AddAccountDialog(onDismiss: () -> Unit, onSave: (AccountCreateBody) -> Unit) {
    var mobile by remember { mutableStateOf("") }
    var province by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }
    var strategy by remember { mutableStateOf("max_inventory") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("添加 i茅台 账号") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(mobile, { mobile = it }, label = { Text("手机号") }, singleLine = true)
                OutlinedTextField(province, { province = it }, label = { Text("省份") }, singleLine = true)
                OutlinedTextField(city, { city = it }, label = { Text("城市") }, singleLine = true)
                OutlinedTextField(address, { address = it }, label = { Text("详细地址") })
                OutlinedTextField(strategy, { strategy = it }, label = { Text("选店策略") }, singleLine = true)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onSave(
                    AccountCreateBody(
                        mobile = mobile.trim(),
                        province = province.trim(),
                        city = city.trim(),
                        detailAddress = address.trim(),
                        shopStrategy = strategy.trim(),
                        receiverName = "",
                        receiverMobile = mobile.trim(),
                    ),
                )
            }) { Text("保存", color = MaotaiRed) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun EditAccountDialog(
    acc: AccountItem,
    onDismiss: () -> Unit,
    onSave: (AccountUpdateBody) -> Unit,
) {
    var province by remember { mutableStateOf(acc.province ?: "") }
    var city by remember { mutableStateOf(acc.city ?: "") }
    var address by remember { mutableStateOf(acc.detailAddress ?: "") }
    var strategy by remember { mutableStateOf(acc.shopStrategy ?: "max_inventory") }
    var receiver by remember { mutableStateOf(acc.receiverName ?: "") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("编辑 ${acc.mobile}") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(receiver, { receiver = it }, label = { Text("收货人") }, singleLine = true)
                OutlinedTextField(province, { province = it }, label = { Text("省份") }, singleLine = true)
                OutlinedTextField(city, { city = it }, label = { Text("城市") }, singleLine = true)
                OutlinedTextField(address, { address = it }, label = { Text("详细地址") })
                OutlinedTextField(strategy, { strategy = it }, label = { Text("选店策略") }, singleLine = true)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onSave(
                    AccountUpdateBody(
                        receiverName = receiver.trim(),
                        province = province.trim(),
                        city = city.trim(),
                        detailAddress = address.trim(),
                        shopStrategy = strategy.trim(),
                    ),
                )
            }) { Text("保存", color = MaotaiRed) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}
