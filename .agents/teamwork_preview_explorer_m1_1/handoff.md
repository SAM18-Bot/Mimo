# Handoff Report: Milestone 1 - Android Local Data Layer (Room DB) Exploration & Specification

## 1. Observation

Direct observations from inspecting the codebase:

- **Original Request & Project Scope**:
  - `ORIGINAL_REQUEST.md`: R1 requires storing data locally using Android Room DB in `com/mimo/app/data/` with `AssignmentEntity` and `DailyStatsEntity`. `DashboardViewModel` must read from and write to local Room DB.
  - `PROJECT.md`: Specifies feature items #1–5, interface contracts, and module paths (`android/app/src/main/java/com/mimo/app/data/`).

- **Gradle Build Configuration**:
  - Top-level `android/build.gradle.kts` (lines 1-6):
    ```kotlin
    plugins {
        id("com.android.application") version "8.2.2" apply false
        id("org.jetbrains.kotlin.android") version "1.9.22" apply false
    }
    ```
  - App-level `android/app/build.gradle.kts` (lines 1-4, 52-86):
    - Uses Kotlin version `1.9.22` and Compose compiler extension `1.5.8`.
    - Lacks Room dependencies (`androidx.room:room-runtime`, `androidx.room:room-ktx`, `androidx.room:room-compiler`).
    - Lacks annotation processing plugin (`kotlin-kapt` or `com.google.devtools.ksp`).

- **Existing Application Architecture & Models**:
  - `com.mimo.app.MimoApplication` (lines 9-34): Standard `Application` class managing notification channel `mimo_roasts`.
  - `com.mimo.app.network.ApiModels`:
    - `Assignment` (lines 39-47): `val id: Int = 0`, `val title: String = ""`, `val subject: String? = null`, `val due_date: String = ""`, `val priority: String = "medium"`, `val status: String = "pending"`, `val notes: String? = null`.
    - `DailyStats` (lines 4-26): Contains `date: String`, `productive_min: Int`, `distracting_min: Int`, `neutral_min: Int`, `focus_score: Double`, etc.
  - `com.mimo.app.ui.DashboardViewModel` (lines 12-87): Currently relies exclusively on Retrofit (`ApiClient.api.getStats()`, `ApiClient.api.getAssignments()`, `ApiClient.api.markAssignmentDone(id)`) and in-memory `MutableStateFlow`s.
  - Directory `com.mimo.app.data` does not exist yet.

## 2. Logic Chain

1. **Gradle Dependency Injection Requirement**:
   - *Observation*: `android/app/build.gradle.kts` currently imports Retrofit, Gson, Compose, and WorkManager, but lacks Room dependencies and an annotation processor.
   - *Deduction*: Adding Room requires applying `kotlin-kapt` (or `ksp`) and declaring `androidx.room:room-runtime:2.6.1`, `androidx.room:room-ktx:2.6.1`, and `kapt("androidx.room:room-compiler:2.6.1")`.

2. **Entity Design Alignment**:
   - *Observation*: `ORIGINAL_REQUEST.md` and `PROJECT.md` require `AssignmentEntity` and `DailyStatsEntity` with sync state tracking (`isSynced`). `ApiModels.kt` defines `Assignment` and `DailyStats`.
   - *Deduction*: `AssignmentEntity` must map Kotlin properties to SQLite columns matching domain types while adding `isSynced: Boolean = false`. Primary key for `AssignmentEntity` should be auto-generating `id: Int = 0` (or client/server assigned ID). Primary key for `DailyStatsEntity` must be `date: String` (`YYYY-MM-DD`).

3. **DAO API Design**:
   - *Observation*: Feature #4 requires reactive streams via Kotlin `Flow` for UI observation and unsynced entity access for `SyncWorker`.
   - *Deduction*: `AssignmentDao` must expose `getAllAssignments(): Flow<List<AssignmentEntity>>`, `getUnsynced(): List<AssignmentEntity>`, `insert`, `update`, `delete`, and `markDone`. `DailyStatsDao` must expose `getStatsFlow(date: String): Flow<DailyStatsEntity?>`, `getByDate(date: String): DailyStatsEntity?`, `insertOrUpdate`, and `getUnsynced()`.

4. **Database Initialization**:
   - *Observation*: Room DB must be instantiated at application scope.
   - *Deduction*: `MimoDatabase.kt` will declare `@Database(entities = [AssignmentEntity::class, DailyStatsEntity::class], version = 1, exportSchema = false)` and provide a singleton `getDatabase(context)` instance via `MimoApplication`.

## 3. Implementation Specifications

### Specs 1: `build.gradle.kts` Modifications

#### 1. Top-Level `android/build.gradle.kts`
```kotlin
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
    id("org.jetbrains.kotlin.kapt") version "1.9.22" apply false
}
```

#### 2. App-Level `android/app/build.gradle.kts`
```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")
}

// Inside dependencies block:
dependencies {
    // Room Database
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    kapt("androidx.room:room-compiler:$roomVersion")
    
    // ... existing dependencies
}
```

---

### Specs 2: `AssignmentEntity.kt`
File: `android/app/src/main/java/com/mimo/app/data/AssignmentEntity.kt`

```kotlin
package com.mimo.app.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mimo.app.network.Assignment

@Entity(tableName = "assignments")
data class AssignmentEntity(
    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "id")
    val id: Int = 0,

    @ColumnInfo(name = "title")
    val title: String,

    @ColumnInfo(name = "subject")
    val subject: String? = null,

    @ColumnInfo(name = "due_date")
    val dueDate: String,

    @ColumnInfo(name = "priority")
    val priority: String = "medium",

    @ColumnInfo(name = "status")
    val status: String = "pending",

    @ColumnInfo(name = "notes")
    val notes: String? = null,

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false
)

fun AssignmentEntity.toDomain(): Assignment {
    return Assignment(
        id = id,
        title = title,
        subject = subject,
        due_date = dueDate,
        priority = priority,
        status = status,
        notes = notes
    )
}

fun Assignment.toEntity(isSynced: Boolean = false): AssignmentEntity {
    return AssignmentEntity(
        id = id,
        title = title,
        subject = subject,
        dueDate = due_date,
        priority = priority,
        status = status,
        notes = notes,
        isSynced = isSynced
    )
}
```

---

### Specs 3: `DailyStatsEntity.kt`
File: `android/app/src/main/java/com/mimo/app/data/DailyStatsEntity.kt`

```kotlin
package com.mimo.app.data

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.mimo.app.network.DailyStats

@Entity(tableName = "daily_stats")
data class DailyStatsEntity(
    @PrimaryKey
    @ColumnInfo(name = "date")
    val date: String,

    @ColumnInfo(name = "productive_min")
    val productiveMin: Int = 0,

    @ColumnInfo(name = "distracting_min")
    val distractingMin: Int = 0,

    @ColumnInfo(name = "neutral_min")
    val neutralMin: Int = 0,

    @ColumnInfo(name = "focus_score")
    val focusScore: Double = 0.0,

    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false
)

fun DailyStatsEntity.toDomain(): DailyStats {
    return DailyStats(
        date = date,
        productive_min = productiveMin,
        distracting_min = distractingMin,
        neutral_min = neutralMin,
        focus_score = focusScore,
        desk_time_min = productiveMin + distractingMin + neutralMin
    )
}

fun DailyStats.toEntity(isSynced: Boolean = false): DailyStatsEntity {
    return DailyStatsEntity(
        date = date,
        productiveMin = productive_min,
        distractingMin = distracting_min,
        neutralMin = neutral_min,
        focusScore = focus_score,
        isSynced = isSynced
    )
}
```

---

### Specs 4: `AssignmentDao.kt`
File: `android/app/src/main/java/com/mimo/app/data/AssignmentDao.kt`

```kotlin
package com.mimo.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface AssignmentDao {
    @Query("SELECT * FROM assignments ORDER BY due_date ASC, id DESC")
    fun getAllAssignments(): Flow<List<AssignmentEntity>>

    @Query("SELECT * FROM assignments WHERE is_synced = 0")
    suspend fun getUnsynced(): List<AssignmentEntity>

    @Query("SELECT * FROM assignments WHERE id = :id LIMIT 1")
    suspend fun getById(id: Int): AssignmentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(assignment: AssignmentEntity): Long

    @Update
    suspend fun update(assignment: AssignmentEntity): Int

    @Delete
    suspend fun delete(assignment: AssignmentEntity)

    @Query("UPDATE assignments SET status = 'done', is_synced = 0 WHERE id = :id")
    suspend fun markDone(id: Int)

    @Query("UPDATE assignments SET is_synced = 1 WHERE id IN (:ids)")
    suspend fun markSynced(ids: List<Int>)
}
```

---

### Specs 5: `DailyStatsDao.kt`
File: `android/app/src/main/java/com/mimo/app/data/DailyStatsDao.kt`

```kotlin
package com.mimo.app.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface DailyStatsDao {
    @Query("SELECT * FROM daily_stats WHERE date = :date LIMIT 1")
    fun getByDateFlow(date: String): Flow<DailyStatsEntity?>

    @Query("SELECT * FROM daily_stats WHERE date = :date LIMIT 1")
    suspend fun getByDate(date: String): DailyStatsEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(stats: DailyStatsEntity)

    @Query("SELECT * FROM daily_stats WHERE is_synced = 0")
    suspend fun getUnsynced(): List<DailyStatsEntity>

    @Query("UPDATE daily_stats SET is_synced = 1 WHERE date IN (:dates)")
    suspend fun markSynced(dates: List<String>)
}
```

---

### Specs 6: `MimoDatabase.kt`
File: `android/app/src/main/java/com/mimo/app/data/MimoDatabase.kt`

```kotlin
package com.mimo.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [AssignmentEntity::class, DailyStatsEntity::class],
    version = 1,
    exportSchema = false
)
abstract class MimoDatabase : RoomDatabase() {
    abstract fun assignmentDao(): AssignmentDao
    abstract fun dailyStatsDao(): DailyStatsDao

    companion object {
        @Volatile
        private var INSTANCE: MimoDatabase? = null

        fun getDatabase(context: Context): MimoDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    MimoDatabase::class.java,
                    "mimo_database"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
```

---

### Specs 7: Application & ViewModel Refactoring Plan

1. **`MimoApplication.kt`**:
   Add lazy property for `MimoDatabase`:
   ```kotlin
   val database: MimoDatabase by lazy { MimoDatabase.getDatabase(this) }
   ```

2. **`DashboardViewModel.kt`**:
   - Inject / reference `AssignmentDao` and `DailyStatsDao`.
   - Observe local database:
     ```kotlin
     val assignments: StateFlow<List<Assignment>> = assignmentDao.getAllAssignments()
         .map { list -> list.map { it.toDomain() } }
         .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
     ```
   - Update `markAssignmentDone(id: Int)` to call `assignmentDao.markDone(id)` locally instead of calling Retrofit API synchronously.
   - Offline fallback in `refresh()`: attempt network fetch to populate Room DB, catching network errors gracefully without crashing or showing error when offline.

## 4. Caveats

- **KSP vs KAPT**: Specification uses `kotlin-kapt` because Kotlin `1.9.22` kapt is bundled with the standard Kotlin Gradle plugin. If KSP is preferred, `com.google.devtools.ksp` version `1.9.22-1.0.17` can be configured.
- **Date Format Assumption**: `date` in `DailyStatsEntity` and `dueDate` in `AssignmentEntity` are stored as ISO String (`YYYY-MM-DD`), matching JSON formats from the backend API.

## 5. Conclusion

The specification provides a complete, local-first Room database solution for Milestone 1. It details missing build dependencies, entity definitions, DAO query methods, database singleton creation, and ViewModel refactoring steps required to meet offline requirements R1.

## 6. Verification Method

1. **Build Verification**:
   - Run `./gradlew assembleDebug` or `gradlew.bat assembleDebug` in `android/` directory after applying changes.
   - Verify code compilation and Room annotation processor code generation.

2. **Database Verification**:
   - Inspect generated DAO implementation classes in `android/app/build/generated/source/kapt/debug/com/mimo/app/data/`.
