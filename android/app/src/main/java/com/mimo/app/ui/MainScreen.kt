package com.mimo.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.mimo.app.ui.tabs.HomeScreen
import com.mimo.app.ui.tabs.ScheduleScreen
import com.mimo.app.ui.tabs.InsightsScreen
import com.mimo.app.ui.tabs.SettingsScreen

enum class TabScreen { Home, Schedule, Insights, Settings }

@Composable
fun MainScreen(viewModel: DashboardViewModel = viewModel()) {
    var currentTab by rememberSaveable { mutableStateOf(TabScreen.Home) }
    var suggestedSubject by rememberSaveable { mutableStateOf<String?>(null) }
    val tabState = androidx.compose.runtime.saveable.rememberSaveableStateHolder()
    val snackbar = remember { SnackbarHostState() }
    val error by viewModel.error.collectAsState()
    LaunchedEffect(error) {
        error?.let {
            snackbar.showSnackbar(it)
            viewModel.dismissError(it)
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                    label = { Text("Home") },
                    selected = currentTab == TabScreen.Home,
                    onClick = { currentTab = TabScreen.Home }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Schedule") },
                    label = { Text("Schedule") },
                    selected = currentTab == TabScreen.Schedule,
                    onClick = { currentTab = TabScreen.Schedule }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Insights, contentDescription = "Insights") },
                    label = { Text("Insights") },
                    selected = currentTab == TabScreen.Insights,
                    onClick = { currentTab = TabScreen.Insights }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    selected = currentTab == TabScreen.Settings,
                    onClick = { currentTab = TabScreen.Settings }
                )
            }
        }
    ) { paddingValues ->
        val modifier = Modifier.padding(paddingValues)
        tabState.SaveableStateProvider(currentTab.name) {
          when (currentTab) {
            TabScreen.Home -> HomeScreen(viewModel, modifier)
            TabScreen.Schedule -> ScheduleScreen(viewModel, modifier, suggestedSubject) { suggestedSubject = null }
            TabScreen.Insights -> InsightsScreen(viewModel, modifier, onTrackSubject = { subject ->
                suggestedSubject = subject
                currentTab = TabScreen.Schedule
            })
            TabScreen.Settings -> SettingsScreen(viewModel, modifier)
          }
        }
    }
}
