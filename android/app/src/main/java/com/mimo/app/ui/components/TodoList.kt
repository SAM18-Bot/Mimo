package com.mimo.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.outlined.Circle
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import com.mimo.app.network.Todo
import java.time.format.DateTimeFormatter
import java.time.ZonedDateTime
import java.time.ZoneId

@Composable
fun TodoList(
    todos: List<Todo>,
    onMarkDone: (Int) -> Unit
) {
    if (todos.isEmpty()) {
        Text(
            text = "No tasks. You're all caught up!",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        return
    }

    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        todos.forEach { todo ->
            val isDone = todo.status == "done"
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = !isDone) { onMarkDone(todo.id) }
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = if (isDone) Icons.Filled.CheckCircle else Icons.Outlined.Circle,
                    contentDescription = if (isDone) "Done" else "Pending",
                    tint = if (isDone) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        text = todo.title,
                        style = MaterialTheme.typography.bodyMedium,
                        textDecoration = if (isDone) TextDecoration.LineThrough else null,
                        color = if (isDone) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface
                    )
                    if (todo.remind_at != null) {
                        val formattedTime = try {
                            val parsed = ZonedDateTime.parse(todo.remind_at)
                            parsed.withZoneSameInstant(ZoneId.systemDefault()).format(DateTimeFormatter.ofPattern("MMM d, h:mm a"))
                        } catch (e: Exception) {
                            todo.remind_at.take(16)
                        }
                        Text(
                            text = "Reminder: $formattedTime",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}
