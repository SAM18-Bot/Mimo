import pytest
from unittest.mock import patch, MagicMock
from modules.ai_layer.daily_report import run_eod_report
from db.models import DailySummary, AccountabilityLog

from datetime import date

def test_run_eod_report(client, db_session):
    # Seed accountability answers
    ans1 = AccountabilityLog(user_id=1, date=date.today(), question="Did you study?", answer="Yes, 2 hours")
    db_session.add(ans1)
    db_session.commit()

    # Mock dependencies
    speak_mock = MagicMock()
    broadcast_mock = MagicMock()
    
    mock_ai_response = {"overall_assessment": "Good", "struggles": "None", "advice": "Keep it up", "summary": "Did well"}

    with patch("modules.ai_layer.daily_report.generate_eod_report", return_value=mock_ai_response):
        with patch("modules.behavior_engine.pattern_detector.get_weekly_patterns", return_value={"insights": ["test"], "weekly_data": "", "peak_productive_hour": 14}):
            run_eod_report(speak_fn=speak_mock, broadcast_fn=broadcast_mock)

    # Check DB
    summary = db_session.query(DailySummary).first()
    assert summary is not None
    assert summary.ai_report_text == str(mock_ai_response)
    
    # Check callbacks
    speak_mock.assert_called()
    broadcast_mock.assert_called()
    
    args, kwargs = broadcast_mock.call_args
    assert args[0]["type"] == "eod_report"
