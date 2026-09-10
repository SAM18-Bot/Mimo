import logging
import threading
import time
from datetime import datetime
from db.database import get_db_ctx
from db.models import Todo
from api.websocket import push_event

log = logging.getLogger(__name__)

class TodoReminderService:
    def __init__(self, poll_interval_s=60):
        self.poll_interval_s = poll_interval_s
        self._stop_event = threading.Event()
        self._stop_event.set()
        self.thread = None

    def start(self):
        if self._stop_event and not self._stop_event.is_set() and self.thread and self.thread.is_alive(): return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="todo-reminders")
        self.thread.start()
        log.info("Todo reminder service started.")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_and_notify()
            except Exception as e:
                log.error(f"Todo reminder error: {e}")
            self._stop_event.wait(self.poll_interval_s)

    def check_and_notify(self):
        with get_db_ctx() as db:
            pending = db.query(Todo).filter(
                Todo.status != 'done',
                Todo.remind_at != None,
                Todo.delivered == False,
                Todo.remind_at <= datetime.now()
            ).all()

            for t in pending:
                msg = f"Time to do: {t.title}"
                


                push_event({
                    "type": "todo_reminder",
                    "user_id": t.user_id,
                    "todo_id": t.id,
                    "message": msg,
                    "ts": datetime.now().isoformat()
                })

                t.delivered = True
            
            db.commit()

_service = TodoReminderService()

def start_todo_reminders():
    _service.start()

def stop_todo_reminders():
    _service.stop()
