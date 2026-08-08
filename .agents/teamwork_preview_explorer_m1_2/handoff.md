# Handoff Report — Milestone 1: DashboardViewModel Refactoring Strategy

**Author**: Explorer 2 (`teamwork_preview_explorer`)  
**Target File**: `c:\Users\samee\projects\Mimo\android\app\src\main\java\com\mimo\app\ui\DashboardViewModel.kt`  
**Working Directory**: `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_2`  
**Date**: 2026-08-07  

---

## 1. Observation

- **`DashboardViewModel.kt` Current State**:
  - File path: `c:\Users\samee\projects\Mimo\android\app\src\main\java\com\mimo\app\ui\DashboardViewModel.kt`
  - Lines 12–30: Defines `StateFlow`s for `_stats`, `_assignments`, `_history`, `_screenBreakdown`, `_isLoading`, `_error`.
  - Lines 36–53 (`init` block) & Lines 60–75 (`refresh()` method): `refresh()` executes on `Dispatchers.IO` making direct Retrofit network calls via `ApiClient.api.getStats()`, `ApiClient.api.getAssignments()`, `ApiClient.api.getHistory()`, and `ApiClient.api.getScreenBreakdown()`.
  - Lines 77–86 (`markAssignmentDone(id: Int)`): Direct Retrofit network call `ApiClient.api.markAssignmentDone(id)` followed by calling `refresh()`.

- **`MimoApplication.kt` Current State**:
  - File path: `c:\Users\samee\projects\Mimo\android\app\src\main\java\com\mimo\app\MimoApplication.kt`
  - Currently handles notification channel creation (`CHANNEL_ID_ROASTS`), but does not yet initialize or expose `MimoDatabase`.

- **`DashboardScreen.kt` & Component Contracts**:
  - File path: `c:\Users\samee\projects\Mimo\android\app\src\main\java\com\mimo\app\ui\DashboardScreen.kt`
  - Collects `stats`, `assignments`, `history`, `screenBreakdown`, `isLoading`, `error` as Compose state via `.collectAsState()`.
  - `AssignmentList.kt` receives `List<Assignment>` and `onMarkDone: (Int) -> Unit`.
  - `StatsRow` receives `DailyStats`.

- **`PROJECT.md` Schema Contract (Milestone 1, Requirement R1)**:
  - Database: `MimoDatabase` with `AssignmentEntity` and `DailyStatsEntity`.
  - `AssignmentEntity` fields: `id: String`, `title: String`, `subject: String?`, `due_date: String`, `priority: String`, `status: String`, `notes: String?`, `isSynced: Boolean`.
  - `DailyStatsEntity` fields: `date: String`, `productive_min: Int`, `distracting_min: Int`, `neutral_min: Int`, `focus_score: Double`, `isSynced: Boolean`.

---

## 2. Logic Chain

1. **Observation 1 & 4**: `DashboardViewModel` currently depends on direct Retrofit API calls (`ApiClient.api.*`) in `refresh()`, which fails completely when network connection is unavailable (violating requirement R1 / offline standalone functionality).
2. **Observation 2**: Room DB instance needs global application context lifecycle access. By exposing `MimoDatabase` singleton via `MimoApplication` (or `MimoDatabase.getInstance(context)`), DAOs can be accessed cleanly by ViewModels and background services.
3. **Step 1 — Room Database & DAO Exposure**:
   - Update `MimoApplication.kt` to hold a singleton `database: MimoDatabase` property initialized in `onCreate()`.
   - `DashboardViewModel` subclasses `AndroidViewModel(application)` or receives DAOs via constructor default params:
     ```kotlin
     class DashboardViewModel(application: Application) : AndroidViewModel(application) {
         private val assignmentDao: AssignmentDao = MimoDatabase.getInstance(application).assignmentDao()
         private val dailyStatsDao: DailyStatsDao = MimoDatabase.getInstance(application).dailyStatsDao()
     ```
4. **Step 2 — Reactive Flow Collection for UI State**:
   - DAOs expose reactive Kotlin `Flow<List<AssignmentEntity>>` and `Flow<DailyStatsEntity?>`.
   - Replace network fetching in `DashboardViewModel` with reactive state flows created via `stateIn()`:
     ```kotlin
     val assignments: StateFlow<List<Assignment>> = assignmentDao.getAllAssignmentsFlow()
         .map { entities -> entities.map { it.toUiModel() } }
         .stateIn(
             scope = viewModelScope,
             started = SharingStarted.WhileSubscribed(5000),
             initialValue = emptyList()
         )

     val stats: StateFlow<DailyStats> = dailyStatsDao.getStatsForDateFlow(getTodayDateString())
         .map { entity -> entity?.toUiModel() ?: DailyStats(date = getTodayDateString(), focus_score = 100.0) }
         .stateIn(
             scope = viewModelScope,
             started = SharingStarted.WhileSubscribed(5000),
             initialValue = DailyStats()
         )
     ```
   - This eliminates the need for imperative network calls; any local DB mutation instantly triggers UI updates reactively.
5. **Step 3 — Local Write Operations with `isSynced = false`**:
   - **Quick-Add Assignment**:
     ```kotlin
     fun addAssignment(title: String, subject: String?, dueDate: String, priority: String = "medium", notes: String? = null) {
         viewModelScope.launch(Dispatchers.IO) {
             val entity = AssignmentEntity(
                 id = "opt-local-${System.currentTimeMillis()}",
                 title = title,
                 subject = subject,
                 due_date = dueDate,
                 priority = priority,
                 status = "pending",
                 notes = notes,
                 isSynced = false
             )
             assignmentDao.insert(entity)
         }
     }
     ```
   - **Mark Assignment Done**:
     ```kotlin
     fun markAssignmentDone(idStringOrInt: Any) {
         viewModelScope.launch(Dispatchers.IO) {
             assignmentDao.markAsDone(id = idStringOrInt.toString(), isSynced = false)
         }
     }
     ```
   - **Update Daily Stats**:
     ```kotlin
     fun updateStats(productiveDelta: Int, distractingDelta: Int, neutralDelta: Int = 0) {
         viewModelScope.launch(Dispatchers.IO) {
             val today = getTodayDateString()
             val current = dailyStatsDao.getStatsForDate(today)
             val prod = (current?.productive_min ?: 0) + productiveDelta
             val dist = (current?.distracting_min ?: 0) + distractingDelta
             val neut = (current?.neutral_min ?: 0) + neutralDelta
             val total = (prod + dist + neut).coerceAtLeast(1)
             val score = ((prod.toDouble() / (prod + dist).coerceAtLeast(1))) * 100.0

             val updated = DailyStatsEntity(
                 date = today,
                 productive_min = prod,
                 distracting_min = dist,
                 neutral_min = neut,
                 focus_score = score,
                 isSynced = false
             )
             dailyStatsDao.insertOrUpdate(updated)
         }
     }
     ```
6. **Observation 3 — UI Compatibility**:
   - Providing model mapping extension functions (`AssignmentEntity.toUiModel()` and `DailyStatsEntity.toUiModel()`) ensures `DashboardScreen.kt`, `AssignmentList.kt`, `FocusScoreGauge.kt`, and `StatsCards.kt` require zero breaking UI changes while operating 100% offline.

---

## 3. Caveats

- **Date Formatting**: `getTodayDateString()` must consistently use ISO `yyyy-MM-DD` format (e.g. `2026-08-07`) matching both Python backend and Room primary keys.
- **ID Type Mapping**: `ApiModels.kt` currently defines `Assignment.id` as `Int`, whereas `PROJECT.md` schema specifies `String` (e.g., `"opt-local-1"`). Implementer should harmonize ID type across `Assignment` and `AssignmentEntity` (using `String` for flexible offline unique ID generation like `opt-local-${System.currentTimeMillis()}`).

---

## 4. Conclusion

The refactoring strategy for `DashboardViewModel.kt` is fully formulated. Replacing direct Retrofit network calls with reactive Room DAO `Flow`s and storing offline mutations with `isSynced = false` establishes a robust local-first architecture fulfilling Requirement R1.

---

## 5. Verification Method

1. **Code Inspection**:
   - Check `DashboardViewModel.kt` contains no direct Retrofit `ApiClient.api.*` calls in state initialization or user action methods.
   - Verify `assignmentDao` and `dailyStatsDao` are used to query and write.
   - Verify all write operations explicitly set `isSynced = false`.
2. **Offline Runtime Verification**:
   - Build Android project: `./gradlew assembleDebug`
   - Run app on emulator in Airplane Mode (network disabled).
   - Perform quick-add assignment, mark assignment done, and verify UI reflects changes immediately from Room DB.
