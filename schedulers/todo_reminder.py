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
        self.running = False
        self.thread = None

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="todo-reminders")
        self.thread.start()
        log.info("Todo reminder service started.")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self.check_and_notify()
            except Exception as e:
                log.error(f"Todo reminder error: {e}")
            time.sleep(self.poll_interval_s)

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
                
                # trigger desktop native popups if available
                try:
                    from desktop.notifications import notify
                    notify("To-Do Reminder", msg)
                except Exception:
                    pass

                push_event({
                    "type": "todo_reminder",
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
