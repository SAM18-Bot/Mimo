# E2E Test Infra: Mimo Standalone & Sync Engine

## Test Philosophy
- Opaque-box, requirement-driven verification for Android Local Data (R1), Mobile Screen Tracking (R2), and Python/Android Sync Engine (R3).
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Room Database & Entities | R1 | 5 | 5 | ✓ |
| 2 | Offline DashboardViewModel | R1 | 5 | 5 | ✓ |
| 3 | Mobile Tracker Service & UsageStats | R2 | 5 | 5 | ✓ |
| 4 | Local Roast Notification Trigger | R2 | 5 | 5 | ✓ |
| 5 | Backend `POST /sync/push` Endpoint | R3 | 5 | 5 | ✓ |
| 6 | Backend `GET /sync/pull` Endpoint | R3 | 5 | 5 | ✓ |
| 7 | Android `SyncWorker` Task | R3 | 5 | 5 | ✓ |

## Test Architecture
- Python Test Runner: `pytest` executing tests in `tests/test_sync.py` and `tests/test_api.py`.
- Android Test Runner: Gradle unit/integration tests running via `./gradlew testDebugUnitTest`.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Offline Usage & Local Task Management | Room DB, Offline ViewModel | Medium |
| 2 | Distraction Detection & Local Roast Alert | MobileTrackerService, UsageStatsManager, Roast Channel | Medium |
| 3 | Offline-to-Online Background Sync | SyncWorker, POST /sync/push, GET /sync/pull, Aggregator | High |

## Coverage Thresholds
- Tier 1: ≥5 tests per feature
- Tier 2: ≥5 boundary/edge tests per feature
- Tier 3: Pairwise feature interaction tests
- Tier 4: Real-world application scenarios
