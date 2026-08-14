import sys
import os
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, r"c:\Users\samee\projects\Mimo")

from db.database import get_db_ctx, init_db
from db.models import User, Assignment, DailySummary, RoastLog
from modules.voice.intent_router import IntentRouter
from sqlalchemy.orm.exc import DetachedInstanceError

def run_empirical_stress_tests():
    print("=== STARTING EMPIRICAL STRESS TESTS FOR INTENT_ROUTER HANDLERS ===")
    init_db()

    # 1. Setup Test User
    with get_db_ctx() as db:
        test_user = db.query(User).filter(User.email == "detached_stress@example.com").first()
        if not test_user:
            test_user = User(email="detached_stress@example.com", display_name="Detached Stress User")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        user_id = test_user.id
    
    print(f"[+] Test user ready with user_id={user_id}")

    # Track spoken and broadcasted messages
    spoken_history = []
    broadcast_history = []

    def mock_speak(msg):
        spoken_history.append(msg)

    def mock_broadcast(msg):
        broadcast_history.append(msg)

    router = IntentRouter(speak_fn=mock_speak, broadcast_fn=mock_broadcast, user_id=user_id)

    # ------------------------------------------------------------------------
    # TEST 1: _handle_add_assignment under detached session
    # ------------------------------------------------------------------------
    print("\n--- Test 1: _handle_add_assignment ---")
    spoken_history.clear()
    broadcast_history.clear()
    
    try:
        router.route("add Physics homework due tomorrow")
        assert len(spoken_history) == 1, f"Expected 1 spoken message, got {len(spoken_history)}"
        assert "Physics" in spoken_history[0], f"Unexpected message: {spoken_history[0]}"
        assert len(broadcast_history) == 1, f"Expected 1 broadcast, got {len(broadcast_history)}"
        assert broadcast_history[0]["type"] == "assignment_added"
        print("[PASS] _handle_add_assignment executed cleanly without DetachedInstanceError")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_add_assignment: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_add_assignment: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 2: _handle_show_tasks under detached session
    # ------------------------------------------------------------------------
    print("\n--- Test 2: _handle_show_tasks ---")
    spoken_history.clear()
    broadcast_history.clear()

    try:
        router.route("show my tasks")
        assert len(spoken_history) == 1
        assert "Physics" in spoken_history[0]
        assert len(broadcast_history) == 1
        assert broadcast_history[0]["type"] == "tasks_list"
        print("[PASS] _handle_show_tasks executed cleanly without DetachedInstanceError")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_show_tasks: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_show_tasks: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 3: _handle_mark_done under detached session
    # ------------------------------------------------------------------------
    print("\n--- Test 3: _handle_mark_done ---")
    spoken_history.clear()
    broadcast_history.clear()

    try:
        router.route("done with Physics")
        assert len(spoken_history) == 1
        assert "Physics" in spoken_history[0]
        print("[PASS] _handle_mark_done executed cleanly without DetachedInstanceError")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_mark_done: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_mark_done: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 4: _handle_productivity under detached session
    # ------------------------------------------------------------------------
    print("\n--- Test 4: _handle_productivity ---")
    spoken_history.clear()
    broadcast_history.clear()

    try:
        router.route("how productive was I")
        assert len(spoken_history) == 1
        assert "focus score" in spoken_history[0].lower()
        print("[PASS] _handle_productivity executed cleanly without DetachedInstanceError")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_productivity: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_productivity: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 5: _handle_what_to_study (Normal Advisor path)
    # ------------------------------------------------------------------------
    print("\n--- Test 5: _handle_what_to_study (Normal path) ---")
    spoken_history.clear()
    broadcast_history.clear()

    try:
        router.route("what should I study")
        assert len(spoken_history) == 1
        assert len(broadcast_history) == 1
        assert broadcast_history[0]["type"] == "study_advice"
        print("[PASS] _handle_what_to_study normal path executed cleanly")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_what_to_study (normal): {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_what_to_study (normal): {e}")
        sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 6: _handle_what_to_study (Advisor Exception Fallback path)
    # ------------------------------------------------------------------------
    print("\n--- Test 6: _handle_what_to_study (Advisor Exception Fallback path) ---")
    spoken_history.clear()
    broadcast_history.clear()

    # Add urgent pending assignment for fallback test
    with get_db_ctx() as db:
        urgent_task = Assignment(
            user_id=user_id,
            title="Urgent Organic Chemistry",
            due_date=date.today() + timedelta(days=1),
            status="pending"
        )
        db.add(urgent_task)
        db.commit()

    with patch("modules.ai_layer.study_advisor.StudyAdvisor.get_next_to_study", side_effect=RuntimeError("Simulated advisor failure")):
        try:
            router.route("what to study")
            assert len(spoken_history) == 1
            assert "Urgent Organic Chemistry" in spoken_history[0]
            assert len(broadcast_history) == 1
            assert "Urgent Organic Chemistry" in broadcast_history[0]["message"]
            print("[PASS] _handle_what_to_study fallback path executed cleanly without DetachedInstanceError!")
        except DetachedInstanceError as e:
            print(f"[FAIL] DetachedInstanceError in _handle_what_to_study (fallback): {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[FAIL] Unexpected exception in _handle_what_to_study (fallback): {e}")
            sys.exit(1)

    # ------------------------------------------------------------------------
    # TEST 7: _handle_eod_report under detached session
    # ------------------------------------------------------------------------
    print("\n--- Test 7: _handle_eod_report ---")
    spoken_history.clear()
    broadcast_history.clear()

    try:
        router.route("end of day report")
        assert len(spoken_history) >= 1
        print("[PASS] _handle_eod_report executed cleanly")
    except DetachedInstanceError as e:
        print(f"[FAIL] DetachedInstanceError in _handle_eod_report: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unexpected exception in _handle_eod_report: {e}")
        sys.exit(1)

    print("\n=== ALL EMPIRICAL STRESS TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_empirical_stress_tests()
