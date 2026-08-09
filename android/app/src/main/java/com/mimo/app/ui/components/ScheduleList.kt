package com.mimo.app.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mimo.app.network.ScheduleBlock

@Composable
fun ScheduleList(
    schedule: List<ScheduleBlock>,
    modifier: Modifier = Modifier
) {
    if (schedule.isEmpty()) {
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "No scheduled blocks for today",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    } else {
        Column(
            modifier = modifier,
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            schedule.forEach { block ->
                ScheduleBlockCard(block = block)
            }
        }
    }
}

@Composable
fun ScheduleBlockCard(block: ScheduleBlock) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (block.kind.lowercase()) {
                "fixed", "school" -> MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.6f)
                "study" -> MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f)
                "break" -> MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.6f)
                else -> MaterialTheme.colorScheme.surfaceVariant
            }
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = block.title.ifBlank { "Study Session" },
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "${block.start_time} - ${block.end_time}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    block.subject?.let { sub ->
                        if (sub.isNotBlank()) {
                            SuggestionChip(
                                onClick = {},
                                label = { Text(sub, style = MaterialTheme.typography.labelSmall) }
                            )
                        }
                    }
                }
            }

            AssistChip(
                onClick = {},
                label = { Text(block.status.replaceFirstChar { it.uppercase() }) }
            )
        }
    }
}
