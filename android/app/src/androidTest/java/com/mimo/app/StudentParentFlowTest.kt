package com.mimo.app

import androidx.compose.ui.test.ComposeTimeoutException
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isEnabled
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onLast
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTextReplacement
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.mimo.app.data.TokenManager
import com.mimo.app.network.AccountApi
import com.mimo.app.network.ApiClient
import com.mimo.app.network.OnboardingRequest
import com.mimo.app.network.PlannerApi
import com.mimo.app.network.RegisterRequest
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeNotNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@OptIn(ExperimentalTestApi::class)
@RunWith(AndroidJUnit4::class)
class StudentParentFlowTest {
    @get:Rule val ui = createEmptyComposeRule()

    private fun waitFor(matcher: SemanticsMatcher) {
        try {
            ui.waitUntil(30_000) {
                ui.onAllNodes(matcher).fetchSemanticsNodes(atLeastOneRootRequired = false).isNotEmpty()
            }
        } catch (cause: ComposeTimeoutException) {
            throw AssertionError("Timed out waiting for ${matcher.description}", cause)
        }
    }

    private fun click(label: String) {
        val matcher = hasText(label)
        waitFor(matcher)
        ui.onAllNodes(matcher).onLast().performClick()
    }

    private fun login(email: String, password: String) {
        waitFor(hasText("Welcome Back"))
        val fields = ui.onAllNodes(hasSetTextAction())
        fields[0].performTextInput(email)
        fields[1].performTextInput(password)
        click("Login")
    }

    private fun startAndResetTimer() {
        ui.onNode(hasText("50m")).performScrollTo().performClick()
        ui.onNode(hasText("Start")).performScrollTo().performClick()
        waitFor(hasText("Pause"))
        click("Pause")
        click("Reset")
        waitFor(hasText("50:00"))
    }

    private fun saveWeeklyPlan() {
        val edit = hasText("Edit schedule") and isEnabled()
        waitFor(edit)
        ui.onNode(edit).performScrollTo().performClick()
        val goal = hasSetTextAction() and hasText("Daily goal (minutes)")
        ui.onNode(goal).performScrollTo().performTextReplacement("90")
        click("Save schedule")
        waitFor(hasText("Schedule saved."))
        val profile = runBlocking { ApiClient.createService(PlannerApi::class.java).profile().body() }
        assertEquals(90, requireNotNull(profile).study_goal_minutes)
    }

    private fun completeTodo() {
        val title = "Review Android notes"
        ui.onNode(hasSetTextAction() and hasText("Task")).performScrollTo().performTextInput(title)
        ui.onNode(hasText("Add to-do")).performScrollTo().performClick()
        val pending = hasText(title) and hasContentDescription("Pending")
        waitFor(pending)
        ui.onNode(pending).performScrollTo().performClick()
        waitFor(hasText(title) and hasContentDescription("Done"))
        val stored = runBlocking { ApiClient.api.getTodos().single { it.title == title } }
        assertEquals("done", stored.status)
    }

    @Test
    fun studentPlansChatsAndLinksParent() {
        val origin = InstrumentationRegistry.getArguments().getString("mimoTestOrigin")
        assumeNotNull(origin)
        require(origin == "https://localhost:18443/")
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        TokenManager.clearToken(context)
        ApiClient.updateBaseUrl(requireNotNull(origin))
        val id = UUID.randomUUID()
        val email = "student-$id@example.org"
        val parentEmail = "parent-$id@example.org"
        val password = UUID.randomUUID().toString()
        runBlocking {
            val student = ApiClient.api.register(RegisterRequest(email, password, display_name = "Device Student"))
            TokenManager.saveToken(context, student.access_token)
            ApiClient.api.completeOnboarding(OnboardingRequest(
                course = "Physics", age = 20, education_level = "undergraduate", ai_engine = "gemini"
            ))
            ApiClient.api.register(RegisterRequest(parentEmail, password, role = "parent"))
            TokenManager.clearToken(context)
        }
        ActivityScenario.launch(MainActivity::class.java).use {
            login(email, password)
            click("Continue")
            waitFor(hasText("Focus timer"))
            startAndResetTimer()
            click("Schedule")
            waitFor(hasText("Weekly schedule"))
            saveWeeklyPlan()
            ui.onNode(hasContentDescription("Add Assignment")).performClick()
            ui.onNode(hasSetTextAction() and hasText("Title")).performTextInput("Device paper")
            click("Add")
            ui.waitUntil(20_000) { runBlocking { ApiClient.api.getAssignments().any { it.title == "Device paper" } } }
            completeTodo()
            click("Insights")
            waitFor(hasText("Coach"))
            ui.onAllNodes(hasSetTextAction()).onFirst().performTextInput("show my tasks")
            click("Send message")
            waitFor(hasText("Device paper", substring = true))
            click("Settings")
            click("Generate Invite Code")
            val invite = hasText("Invite Code: ", substring = true)
            waitFor(invite)
            val inviteText = ui.onNode(invite).fetchSemanticsNode().config[
                androidx.compose.ui.semantics.SemanticsProperties.Text].single().text
            val code = inviteText.substringAfter("Invite Code: ")
            assertEquals(12, code.length)
            ui.onNode(hasText("Use server key")).performScrollTo().performClick()
            waitFor(hasText("Using the server key."))
            ui.onNode(hasText("Sign out")).performScrollTo().performClick()
            login(parentEmail, password)
            val linkField = hasSetTextAction() and hasText("Student invite code")
            waitFor(linkField)
            ui.onNode(linkField).performTextInput(code)
            click("Link student")
            waitFor(hasText("Device Student"))
            waitFor(hasText("Weekly summary"))
            runBlocking {
                assertEquals("Device Student", ApiClient.createService(AccountApi::class.java).children().single().display_name)
            }
        }
    }
}
