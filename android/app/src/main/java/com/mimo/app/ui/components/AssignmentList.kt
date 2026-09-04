package com.mimo.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mimo.app.network.Assignment
import com.mimo.app.ui.theme.MimoColors
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

@Composable
fun AssignmentList(
    assignments: List<Assignment>,
    onMarkDone: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        assignments.forEach { assignment ->
            AssignmentCard(
                assignment = assignment,
                onMarkDone = { onMarkDone(assignment.id) }
            )
        }
    }
}

@Composable
fun AssignmentCard(
    assignment: Assignment,
    onMarkDone: () -> Unit
) {
    val today = LocalDate.now()
    val dueDate = runCatching { LocalDate.parse(assignment.due_date) }.getOrNull()

    val (statusColor, statusText) = if (dueDate != null) {
        val daysUntilDue = ChronoUnit.DAYS.between(today, dueDate)
        when {
            daysUntilDue < 0 -> MaterialTheme.colorScheme.error to "Overdue"
            daysUntilDue == 0L -> MimoColors.Warning to "Due Today"
            else -> MimoColors.Success to "In ${daysUntilDue} days"
        }
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant to (if (assignment.due_date.isBlank()) "No due date" else assignment.due_date)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onMarkDone),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha=0.1f)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = assignment.title,
                    color = MaterialTheme.colorScheme.onBackground,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (assignment.subject != null) {
                        Surface(
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f),
                            shape = RoundedCornerShape(4.dp)
                        ) {
                            Text(
                                text = assignment.subject,
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(
                        text = statusText,
                        color = statusColor,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
            Checkbox(
                checked = assignment.status == "done",
                onCheckedChange = { onMarkDone() },
                colors = CheckboxDefaults.colors(
                    checkedColor = MimoColors.Success,
                    uncheckedColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
        }
    }
}
