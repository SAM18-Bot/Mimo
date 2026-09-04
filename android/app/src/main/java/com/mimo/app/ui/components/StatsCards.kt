package com.mimo.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mimo.app.network.DailyStats
import com.mimo.app.network.ScreenBreakdown
import com.mimo.app.ui.theme.MimoColors

fun formatMinutes(minutes: Int): String {
    if (minutes < 60) return "${minutes}m"
    val hrs = minutes / 60
    val mins = minutes % 60
    return if (mins > 0) "${hrs}h ${mins}m" else "${hrs}h"
}

@Composable
fun StatsRow(
    stats: DailyStats,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatCard(
            modifier = Modifier.weight(1f),
            icon = "⏱️",
            value = formatMinutes(stats.productive_min),
            label = "Productive"
        )
        StatCard(
            modifier = Modifier.weight(1f),
            icon = "📱",
            value = formatMinutes(stats.distracting_min),
            label = "Distracting"
        )
        StatCard(
            modifier = Modifier.weight(1f),
            icon = "🔥",
            value = "${stats.distraction_count}",
            label = "Distractions"
        )
    }
}

@Composable
fun StatCard(
    icon: String,
    value: String,
    label: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha=0.1f)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(text = icon, fontSize = 24.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = value,
                color = MaterialTheme.colorScheme.onBackground,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = label,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp
            )
        }
    }
}

@Composable
fun ScreenTimeBar(
    breakdown: ScreenBreakdown,
    modifier: Modifier = Modifier
) {
    val total = (breakdown.productive_min + breakdown.distracting_min + breakdown.neutral_min).coerceAtLeast(1)
    val productiveWeight = breakdown.productive_min.toFloat() / total
    val distractingWeight = breakdown.distracting_min.toFloat() / total
    val neutralWeight = breakdown.neutral_min.toFloat() / total

    Column(modifier = modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Text(
            text = "Screen Time Usage",
            color = MaterialTheme.colorScheme.onBackground,
            fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(bottom = 8.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(24.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant)
        ) {
            if (productiveWeight > 0f) {
                Box(
                    modifier = Modifier
                        .weight(productiveWeight)
                        .fillMaxHeight()
                        .background(MimoColors.Success)
                )
            }
            if (neutralWeight > 0f) {
                Box(
                    modifier = Modifier
                        .weight(neutralWeight)
                        .fillMaxHeight()
                        .background(MimoColors.Secondary)
                )
            }
            if (distractingWeight > 0f) {
                Box(
                    modifier = Modifier
                        .weight(distractingWeight)
                        .fillMaxHeight()
                        .background(MaterialTheme.colorScheme.error)
                )
            }
        }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            LegendItem(color = MimoColors.Success, label = "Productive")
            LegendItem(color = MimoColors.Secondary, label = "Neutral")
            LegendItem(color = MaterialTheme.colorScheme.error, label = "Distracting")
        }
    }
}

@Composable
private fun LegendItem(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(RoundedCornerShape(5.dp))
                .background(color)
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(text = label, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
    }
}
