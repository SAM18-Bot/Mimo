package com.mimo.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
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
    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        items(assignments) { assignment ->
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
    val dueDate = LocalDate.parse(assignment.due_date) // Assuming ISO format YYYY-MM-DD
    val daysUntilDue = ChronoUnit.DAYS.between(today, dueDate)

    val (statusColor, statusText) = when {
        daysUntilDue < 0 -> MimoColors.Error to "Overdue"
        daysUntilDue == 0L -> MimoColors.Warning to "Due Today"
        else -> MimoColors.Success to "In ${daysUntilDue} days"
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onMarkDone),
        colors = CardDefaults.cardColors(containerColor = MimoColors.Surface),
        border = BorderStroke(1.dp, MimoColors.CardBorder),
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
                    color = MimoColors.TextPrimary,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (assignment.subject != null) {
                        Surface(
                            color = MimoColors.Primary.copy(alpha = 0.2f),
                            shape = RoundedCornerShape(4.dp)
                        ) {
                            Text(
                                text = assignment.subject,
                                color = MimoColors.Primary,
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
                    uncheckedColor = MimoColors.TextSecondary
                )
            )
        }
    }
}
