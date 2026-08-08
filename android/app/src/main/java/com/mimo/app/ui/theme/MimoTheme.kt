package com.mimo.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Mimo color palette (matching web dashboard dark theme)
object MimoColors {
    val Background = Color(0xFF0F0F1A)
    val Surface = Color(0xFF1A1A2E)
    val SurfaceVariant = Color(0xFF232340)
    val Primary = Color(0xFF6C63FF)      // Purple accent
    val PrimaryVariant = Color(0xFF5A52D5)
    val Secondary = Color(0xFF00D9FF)     // Cyan accent
    val Accent = Color(0xFFFF6B6B)        // Coral/red accent
    val Success = Color(0xFF4ADE80)       // Green
    val Warning = Color(0xFFFBBF24)       // Yellow
    val Error = Color(0xFFFF4757)         // Red
    val TextPrimary = Color(0xFFFFFFFF)
    val TextSecondary = Color(0xFFB0B0C8)
    val TextMuted = Color(0xFF6B6B8D)
    val CardBorder = Color(0xFF2A2A4A)
}

private val MimoDarkColorScheme = darkColorScheme(
    primary = MimoColors.Primary,
    onPrimary = MimoColors.TextPrimary,
    secondary = MimoColors.Secondary,
    onSecondary = MimoColors.TextPrimary,
    background = MimoColors.Background,
    onBackground = MimoColors.TextPrimary,
    surface = MimoColors.Surface,
    onSurface = MimoColors.TextPrimary,
    surfaceVariant = MimoColors.SurfaceVariant,
    onSurfaceVariant = MimoColors.TextSecondary,
    error = MimoColors.Error,
    onError = MimoColors.TextPrimary
)

@Composable
fun MimoTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = MimoDarkColorScheme,
        content = content
    )
}
