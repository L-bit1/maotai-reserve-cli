package com.maotai.reserve

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.maotai.reserve.ui.components.LoadingBlock
import com.maotai.reserve.ui.screens.AccountsScreen
import com.maotai.reserve.ui.screens.HomeScreen
import com.maotai.reserve.ui.screens.LoginScreen
import com.maotai.reserve.ui.screens.LotteryScreen
import com.maotai.reserve.ui.screens.ReserveScreen
import com.maotai.reserve.ui.components.UpdateCheckHost
import com.maotai.reserve.ui.theme.MaotaiRed
import com.maotai.reserve.ui.theme.MaotaiTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val session = (application as MaotaiApp).session
        setContent {
            MaotaiTheme {
                val token by session.tokenFlow.collectAsState(initial = null)
                var sessionReady by remember { mutableStateOf(false) }

                LaunchedEffect(Unit) {
                    session.setOnUnauthorizedListener { }
                }

                LaunchedEffect(token) {
                    if (token.isNullOrBlank()) {
                        sessionReady = true
                        return@LaunchedEffect
                    }
                    sessionReady = false
                    session.validateSession()
                    sessionReady = true
                }

                when {
                    token.isNullOrBlank() -> LoginScreen()
                    !sessionReady -> LoadingBlock()
                    else -> MainTabs()
                }
            }
        }
    }
}

@Composable
private fun MainTabs() {
    val session = (androidx.compose.ui.platform.LocalContext.current.applicationContext as MaotaiApp).session
    val baseUrl by session.baseUrlFlow.collectAsState(initial = session.baseUrlBlocking())
    var tab by remember { mutableIntStateOf(0) }

    UpdateCheckHost(baseUrl = baseUrl, session = session)

    Scaffold(
        bottomBar = {
            NavigationBar {
                val items = listOf(
                    Triple(0, Icons.Default.Home, "首页"),
                    Triple(1, Icons.Default.Person, "账号"),
                    Triple(2, Icons.Default.List, "预约"),
                    Triple(3, Icons.Default.Star, "中签"),
                )
                items.forEach { (idx, icon, label) ->
                    NavigationBarItem(
                        selected = tab == idx,
                        onClick = { tab = idx },
                        icon = { Icon(icon, contentDescription = label) },
                        label = { Text(label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaotaiRed,
                            selectedTextColor = MaotaiRed,
                            indicatorColor = MaotaiRed.copy(alpha = 0.12f),
                        ),
                    )
                }
            }
        },
    ) { pad ->
        when (tab) {
            0 -> HomeScreen(
                onOpenAccounts = { tab = 1 },
                onOpenLottery = { tab = 3 },
                modifier = Modifier.padding(pad),
            )
            1 -> AccountsScreen(Modifier.padding(pad))
            2 -> ReserveScreen(Modifier.padding(pad))
            3 -> LotteryScreen(Modifier.padding(pad))
        }
    }
}
