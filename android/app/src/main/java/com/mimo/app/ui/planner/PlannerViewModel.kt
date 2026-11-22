package com.mimo.app.ui.planner

import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mimo.app.network.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.time.LocalDate

class PlannerViewModel : ViewModel() {
    private val api = ApiClient.createService(PlannerApi::class.java)
    var week by mutableStateOf(emptyList<ScheduleBlock>())
        private set
    var profile by mutableStateOf<PlannerProfile?>(null)
        private set
    var loaded by mutableStateOf(false)
        private set
    var busy by mutableStateOf(false)
        private set
    var feedback by mutableStateOf<String?>(null)
        private set
    var suggestions by mutableStateOf<List<String>?>(null)
        private set
    var draft by mutableStateOf<ScheduleDraft?>(null)
    var selectedDate by mutableStateOf(LocalDate.now())
        private set

    fun selectDate(date: LocalDate) {
        selectedDate = date
        suggestions = null
        feedback = null
    }

    private fun perform(action: suspend () -> Unit) {
        if (busy) return
        busy = true
        feedback = null
        viewModelScope.launch {
            try {
                action()
            } catch (e: CancellationException) {
                throw e
            } catch (e: HttpException) {
                feedback = if (e.code() == 422) "Check the dates and times and try again." else "Server returned ${e.code()}. Please retry."
            } catch (_: java.io.IOException) {
                feedback = "Could not reach Mimo. Check your connection and retry."
            } finally {
                busy = false
            }
        }
    }

    private suspend fun loadWeek() {
        val response = api.profile()
        if (!response.isSuccessful) throw HttpException(response)
        val blocks = api.week()
        profile = response.body()
        week = blocks
        loaded = true
        suggestions = null
    }

    fun refresh() = perform { loadWeek() }

    fun edit(subject: String? = null) {
        if (loaded) draft = (draft ?: ScheduleDraft.from(profile, week)).withSubject(subject)
    }

    fun build() {
        val form = draft ?: return
        if (form.validationError() != null) return
        perform {
            val plan = api.build(form.request())
            profile = plan.profile
            week = plan.blocks
            suggestions = null
            draft = null
            feedback = "Schedule saved."
        }
    }

    fun changeStatus(block: ScheduleBlock, status: String) = perform {
        val updated = api.setStatus(block.id, BlockStatus(status))
        week = week.map { if (it.id == updated.id) updated else it }
        suggestions = null
    }

    fun adjust(reschedule: Boolean) = perform {
        val date = selectedDate.toString()
        val updated = if (reschedule) api.reschedule(date) else api.boost(date)
        // Rescheduling also changes the original block's status.
        week = api.week()
        suggestions = null
        feedback = if (updated.isEmpty()) "No blocks added for this day." else "${updated.size} block(s) added for this day."
    }

    fun loadSuggestions() = perform {
        suggestions = api.suggestions(selectedDate.toString()).suggestions.map { it.message.substringBefore(" Use POST /schedule/") }
    }

    fun quickAdd(text: String, time: String?, onSaved: () -> Unit) = perform {
        api.quickAdd(AssignmentCommand(text.trim(), time))
        onSaved()
        feedback = "Assignment added."
    }
}
