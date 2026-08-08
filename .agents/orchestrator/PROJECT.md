# Project: Mimo Native Kotlin Android Application

## Architecture
- Target Workspace: `c:\Users\samee\projects\Mimo\android`
- Language & Framework: Kotlin, Jetpack Compose, Material 3, Coroutines, StateFlow
- Networking & Async: Retrofit 2, OkHttp 4 (REST + WebSocket), Gson / kotlinx.serialization
- Background Processing: Android Foreground Service (`MimoRoastService`) holding persistent OkHttp WebSocket listener + NotificationManager for real-time roast alerts
- Data Flow: Backend (FastAPI `http://10.0.2.2:8000` / `ws://10.0.2.2:8000/ws`) -> RemoteDataSource -> Repository -> ViewModel (StateFlow) -> Compose UI / Notification Service

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Android Project Initialization | Gradle wrapper, build.gradle.kts, Compose setup, AndroidManifest.xml, permissions | M1 | survey_1 |
| 2 | Backend REST API Models & Client | Retrofit client for `/reports/stats`, `/reports/history`, `/assignments/`, `/screen/breakdown` | M2 | survey_2 |
| 3 | WebSocket Client & Roast Listener | OkHttp WebSocket connection to `/ws` parsing `roast`, `stats_update`, `tasks_list` events | M2 | survey_2 |
| 4 | Focus Score Gauge Composable | Animated Canvas-based circular gauge with sweep gradient (0-100 score + letter grade) | M3 | survey_3 |
| 5 | Key Statistics Cards Composable | Productive/distracting minutes, streak days, grade cards | M3 | survey_3 |
| 6 | Tasks & Assignments List Composable | Color-coded urgency indicators, check-to-complete (`POST /assignments/{id}/done`), quick-add input (`POST /assignments/nlp`) | M3 | survey_3 |
| 7 | App Usage Breakdown Composable | Category minutes breakdown (productive/distracting/neutral) & top apps list | M3 | survey_3 |
| 8 | Background Roast Service | `MimoRoastService` persistent service receiving real-time WebSocket roast events in background | M4 | survey_3 |
| 9 | Roast System Notifications | NotificationChannel, high-priority heads-up system alert surfacing roast text | M4 | survey_3 |
| 10| E2E Test Suite & Forensic Audit | Unit tests, Gradle assemble & test verification, mock roast alert trigger verification, benchmark audit | M5 | dual_track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Project Setup & Build Infra | Gradle setup, build.gradle.kts, AndroidManifest, MainActivity shell | none | IN_PROGRESS |
| M2 | Backend API & WebSocket Data Layer | Retrofit REST interfaces, OkHttp WS listener, Data DTOs, Repository | M1 | PLANNED |
| M3 | Jetpack Compose Dashboard UI | Focus Score gauge, Stats cards, Tasks list with quick-add/done, App breakdown | M2 | PLANNED |
| M4 | Background Roast Enforcement Service | `MimoRoastService`, WebSocket roast listener, NotificationManager system alerts | M2, M3 | PLANNED |
| M5 | E2E Testing & Forensic Audit | Pass 100% test suite, build assembleDebug, mock roast notification verification, CLEAN forensic audit | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### Android Client ↔ FastAPI Backend (`http://10.0.2.2:8000`)
- `GET /reports/stats` -> `{"focus_score": int, "productive_minutes": int, "distracting_minutes": int, "streak_days": int, "grade": string}`
- `GET /reports/history` -> `[{"date": string, "score": int}]`
- `GET /assignments/` -> `[{"id": string, "title": string, "subject": string, "due_date": string, "priority": string, "status": string}]`
- `POST /assignments/nlp` -> Request: `{"text": string}` -> Response: assignment object
- `POST /assignments/{id}/done` -> Response: `{"status": "completed"}`
- `GET /screen/breakdown` -> `{"productive_minutes": int, "distracting_minutes": int, "neutral_minutes": int, "top_apps": [{"name": string, "minutes": int}]}`
- `WebSocket /ws` -> Incoming JSON: `{"type": "roast", "message": string, "trigger": string, "app": string, "ts": string}`

## Code Layout
`c:\Users\samee\projects\Mimo\android`
```
android/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── gradlew / gradlew.bat
├── gradle/wrapper/
│   └── gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    └── src/
        └── main/
            ├── AndroidManifest.xml
            ├── res/
            └── java/com/mimo/app/
                ├── MainActivity.kt
                ├── MimoApplication.kt
                ├── data/
                │   ├── api/ (MimoApiService.kt, MimoWebSocketClient.kt)
                │   ├── model/ (Stats.kt, Assignment.kt, UsageBreakdown.kt, RoastEvent.kt)
                │   └── repository/ (MimoRepository.kt)
                ├── service/
                │   └── MimoRoastService.kt (Foreground Service & Notification Manager)
                └── ui/
                    ├── theme/ (Color.kt, Theme.kt, Type.kt)
                    ├── components/ (FocusGauge.kt, StatsCards.kt, AssignmentList.kt, BreakdownCard.kt)
                    └── dashboard/ (DashboardScreen.kt, DashboardViewModel.kt)
```
