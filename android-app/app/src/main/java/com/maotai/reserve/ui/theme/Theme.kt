package com.maotai.reserve.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val MaotaiRed = Color(0xFFC41E3A)
val MaotaiRedDark = Color(0xFF9B1830)
val MaotaiGold = Color(0xFFD4AF37)
val SuccessGreen = Color(0xFF2E7D32)
val WarningOrange = Color(0xFFE65100)
val SurfaceTint = Color(0xFFFFF8F8)

private val LightColors = lightColorScheme(
    primary = MaotaiRed,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFFDAD6),
    onPrimaryContainer = Color(0xFF410009),
    secondary = MaotaiRedDark,
    onSecondary = Color.White,
    tertiary = MaotaiGold,
    background = Color(0xFFFFFBFF),
    surface = Color.White,
    surfaceVariant = Color(0xFFF5F5F5),
    onSurfaceVariant = Color(0xFF5C5C5C),
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFFFB3B0),
    onPrimary = Color(0xFF680014),
    primaryContainer = MaotaiRedDark,
    onPrimaryContainer = Color(0xFFFFDAD6),
    secondary = Color(0xFFFFB3B0),
    background = Color(0xFF1A1112),
    surface = Color(0xFF241819),
    surfaceVariant = Color(0xFF3A2A2C),
)

@Composable
fun MaotaiTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    MaterialTheme(
        colorScheme = if (dark) DarkColors else LightColors,
        content = content,
    )
}
