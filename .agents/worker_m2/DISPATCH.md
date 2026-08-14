## 2026-08-13T09:21:47Z

Worker M2 Assignment: Milestone M2 — Fix Cross-Tenant Data Leaks & WebSocket Multi-Tenancy (Requirement R2)

Tasks:
1. `modules/schedule/manager.py`:
   - `boost_subject_priority()`: filter `Assignment` query by `.filter(Assignment.user_id == user_id)`.
   - `smart_suggestions()`: filter `Assignment` query by `.filter(Assignment.user_id == user_id)`.
   - `update_block_status()`: accept `user_id` parameter and check block ownership against `ScheduleProfile.user_id` so users can only update their own schedule blocks.
2. `modules/ai_layer/roast_engine.py::_get_context()`:
   - Filter nearest-due `Assignment` query by `.filter(Assignment.user_id == user_id)`.
3. `api/websocket.py` & call sites:
   - Refactor `ConnectionManager` to track user connections: `self._user_sockets: Dict[int, Set[WebSocket]] = defaultdict(set)`.
   - Update `connect(websocket, user_id)` and `disconnect(websocket, user_id)`.
   - Add `async def unicast(self, user_id: int, message: Union[dict, str])` to send payloads only to that user's active sockets.
   - Update `broadcast(self, message: Union[dict, str], user_id: Optional[int] = None)` to unicast when `user_id` is specified.
   - Update broadcast call sites in `main.py`, `schedulers/daily_trigger.py`, `modules/assignments/reminder.py`, `modules/cv_pipeline/presence.py`, and `modules/ai_layer/roast_engine.py` to route messages by `user_id`.
