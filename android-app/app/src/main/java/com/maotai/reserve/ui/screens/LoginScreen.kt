package com.maotai.reserve.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.maotai.reserve.MaotaiApp
import com.maotai.reserve.data.LoginRequest
import com.maotai.reserve.data.requireOk
import com.maotai.reserve.ui.components.MaotaiHeroHeader
import com.maotai.reserve.ui.components.ErrorBanner
import com.maotai.reserve.ui.components.UpdateCheckHost
import com.maotai.reserve.ui.theme.MaotaiRed
import kotlinx.coroutines.launch

@Composable
fun LoginScreen() {
    val app = androidx.compose.ui.platform.LocalContext.current.applicationContext as MaotaiApp
    val session = app.session
    val baseUrl by session.baseUrlFlow.collectAsState(initial = session.baseUrlBlocking())
    var serverUrl by remember(baseUrl) { mutableStateOf(baseUrl) }
    var username by remember { mutableStateOf("admin") }
    var password by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    UpdateCheckHost(baseUrl = serverUrl, session = session)

    Column(Modifier.fillMaxSize()) {
        MaotaiHeroHeader(
            title = "茅台预约助手",
            subtitle = "连接云服务器 · 管理 i茅台 账号预约",
        )
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
            ) {
                Column(
                    Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(
                        "登录管理后台",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    OutlinedTextField(
                        value = serverUrl,
                        onValueChange = { serverUrl = it },
                        label = { Text("服务器地址") },
                        placeholder = { Text("http://IP/api/v1/") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        colors = fieldColors(),
                    )
                    OutlinedTextField(
                        value = username,
                        onValueChange = { username = it },
                        label = { Text("用户名") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        colors = fieldColors(),
                    )
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("密码") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        colors = fieldColors(),
                    )
                }
            }

            error?.let { ErrorBanner(message = it, onDismiss = { error = null }) }

            Button(
                onClick = {
                    scope.launch {
                        loading = true
                        error = null
                        try {
                            val url = session.normalizeBaseUrl(serverUrl.trim())
                            session.saveBaseUrl(url)
                            val api = session.api(url, null)
                            val res = api.login(LoginRequest(username.trim(), password))
                            res.requireOk()
                            val token = res.data?.accessToken ?: throw IllegalStateException("无 token")
                            session.saveToken(token)
                        } catch (e: Exception) {
                            error = session.unwrapApiError(e)
                        } finally {
                            loading = false
                        }
                    }
                },
                enabled = !loading && password.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaotaiRed),
            ) {
                if (loading) {
                    CircularProgressIndicator(
                        modifier = Modifier.height(22.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text("登录", style = MaterialTheme.typography.titleMedium)
                }
            }

            Text(
                "预约在服务器执行；中签后请打开官方 i茅台 App 付款",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = MaotaiRed,
    focusedLabelColor = MaotaiRed,
    cursorColor = MaotaiRed,
)
