package com.mimo.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Mimo color palette - Orange Theme
object MimoColors {
    val Primary = Color(0xFFF97316)      // Orange 500
    val PrimaryVariant = Color(0xFFEA580C)
    
    // Dark mode
    val DarkBackground = Color(0xFF000000)
    val DarkSurface = Color(0xFF0A0A0A)
    val DarkSurfaceVariant = Color(0xFF141414)
    val DarkTextPrimary = Color(0xFFFFFFFF)
    val DarkTextSecondary = Color(0xFFA0A0C0)
    
    // Light mode
    val LightBackground = Color(0xFFFFFFFF)
    val LightSurface = Color(0xFFFAFAFA)
    val LightSurfaceVariant = Color(0xFFF4F4F5)
    val LightTextPrimary = Color(0xFF000000)
    val LightTextSecondary = Color(0xFF475569)
    
    val Secondary = Color(0xFF00D9FF)     // Cyan accent
    val Error = Color(0xFFFF4757)
    val Success = Color(0xFF4ADE80)
    val Warning = Color(0xFFFBBF24)
}

private val MimoDarkColorScheme = darkColorScheme(
    primary = MimoColors.Primary,
    onPrimary = MimoColors.DarkTextPrimary,
    secondary = MimoColors.Secondary,
    onSecondary = MimoColors.DarkTextPrimary,
    background = MimoColors.DarkBackground,
    onBackground = MimoColors.DarkTextPrimary,
    surface = MimoColors.DarkSurface,
    onSurface = MimoColors.DarkTextPrimary,
    surfaceVariant = MimoColors.DarkSurfaceVariant,
    onSurfaceVariant = MimoColors.DarkTextSecondary,
    error = MimoColors.Error,
    onError = MimoColors.DarkTextPrimary
)

private val MimoLightColorScheme = lightColorScheme(
    primary = MimoColors.Primary,
    onPrimary = MimoColors.LightTextPrimary,
    secondary = MimoColors.Secondary,
    onSecondary = MimoColors.LightTextPrimary,
    background = MimoColors.LightBackground,
    onBackground = MimoColors.LightTextPrimary,
    surface = MimoColors.LightSurface,
    onSurface = MimoColors.LightTextPrimary,
    surfaceVariant = MimoColors.LightSurfaceVariant,
    onSurfaceVariant = MimoColors.LightTextSecondary,
    error = MimoColors.Error,
    onError = MimoColors.LightTextPrimary
)

@Composable
fun MimoTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colors = if (darkTheme) MimoDarkColorScheme else MimoLightColorScheme
    
    MaterialTheme(
        colorScheme = colors,
        content = content
    )
}
