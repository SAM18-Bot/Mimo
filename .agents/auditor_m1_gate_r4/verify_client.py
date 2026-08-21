import sys
import os
sys.path.insert(0, os.path.abspath("."))

import unittest.mock as mock
import json
import time
import modules.ai_layer.client as c
import config

print("=== Running Forensic Verification of modules/ai_layer/client.py ===")

eod_context = {
    "date": "2026-08-20",
    "productive_min": 120,
    "productive_apps": "VSCode",
    "distracting_min": 15,
    "distracting_apps": "Reddit",
    "desk_time_min": 140,
    "focus_score": 85,
    "distraction_count": 2,
    "longest_focus_min": 45,
    "peak_hour": "14:00",
    "due_today": "None",
    "submitted_today": "Math HW",
    "overdue_list": "None",
    "upcoming_list": "Physics Lab",
    "accountability_answers": "None",
}

study_context = {
    "profile_notes": "CS Student Year 2",
    "weekly_data": "High activity Mon-Wed",
    "weak_subjects": "Math",
    "peak_window": "2:00 PM",
    "avg_study_min": 90,
    "completion_rate": 80,
}

# Test 1: Markdown code fence stripping in generate_eod_report
with mock.patch.object(c, '_chat', return_value='```json\n{"summary": "Great job", "focus_score_comment": "High focus"}\n```'):
    res = c.generate_eod_report(eod_context)
    assert res == {"summary": "Great job", "focus_score_comment": "High focus"}, f"Failed test 1: {res}"
print("Test 1 Passed: EOD markdown stripping")

# Test 2: Raw JSON in generate_eod_report
with mock.patch.object(c, '_chat', return_value='{"summary": "Raw json"}'):
    res = c.generate_eod_report(eod_context)
    assert res == {"summary": "Raw json"}, f"Failed test 2: {res}"
print("Test 2 Passed: EOD raw JSON")

# Test 3: Invalid JSON returns None
with mock.patch.object(c, '_chat', return_value='not a valid json'):
    res = c.generate_eod_report(eod_context)
    assert res is None, f"Failed test 3: {res}"
print("Test 3 Passed: EOD invalid JSON handling")

# Test 4: Empty string from _chat returns None
with mock.patch.object(c, '_chat', return_value=None):
    res = c.generate_eod_report(eod_context)
    assert res is None, f"Failed test 4: {res}"
print("Test 4 Passed: EOD None response handling")

# Test 5: generate_study_recommendations with markdown code fences
with mock.patch.object(c, '_chat', return_value='```json\n{"recommendations": [{"recommendation": "Study Math", "priority": "high"}], "suggested_subjects": ["Math"]}\n```'):
    res = c.generate_study_recommendations(study_context)
    assert res["suggested_subjects"] == ["Math"], f"Failed test 5: {res}"
print("Test 5 Passed: Study recs markdown stripping")

# Test 6: generate_study_recommendations legacy list format
with mock.patch.object(c, '_chat', return_value='[{"recommendation": "Study Physics"}]'):
    res = c.generate_study_recommendations(study_context)
    assert res == {"recommendations": [{"recommendation": "Study Physics"}], "suggested_subjects": []}, f"Failed test 6: {res}"
print("Test 6 Passed: Study recs legacy list format")

# Test 7: generate_roast fallback when AI is disabled
config.LIVE_ROAST_USE_AI = False
roast = c.generate_roast("distraction", "YouTube", 30, "Math HW", 1)
assert isinstance(roast, str) and len(roast) > 0, f"Failed test 7: {roast}"
print("Test 7 Passed: Roast fallback")

# Test 8: generate_roast with AI enabled
config.LIVE_ROAST_USE_AI = True
with mock.patch.object(c, '_chat', return_value="Stop watching YouTube!"):
    roast = c.generate_roast("distraction", "YouTube", 30, "Math HW", 1)
    assert roast == "Stop watching YouTube!", f"Failed test 8: {roast}"
print("Test 8 Passed: Roast AI call")

# Test 9: generate_coach_response
with mock.patch.object(c, '_chat', return_value="A linked list is a linear data structure."):
    resp = c.generate_coach_response("What is a linked list?", {})
    assert resp == "A linked list is a linear data structure.", f"Failed test 9: {resp}"
print("Test 9 Passed: Coach response")

# Test 10: generate_coach_response offline fallback
with mock.patch.object(c, '_chat', return_value=None):
    resp = c.generate_coach_response("What is a linked list?", {})
    assert "offline" in resp, f"Failed test 10: {resp}"
print("Test 10 Passed: Coach response fallback")

# Test 11: _chat without any API key
with mock.patch.object(config, 'GEMINI_API_KEY', None):
    chat_res = c._chat("sys", "user", api_key=None)
    assert chat_res is None, f"Failed test 11: {chat_res}"
print("Test 11 Passed: _chat no API key handling")

# Test 12: _chat with mock genai client to verify correct API invocation
class MockResponse:
    def __init__(self, text):
        self.text = text

class MockGenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.models = self

    def generate_content(self, model, contents, config):
        self.called_model = model
        self.called_contents = contents
        self.called_config = config
        return MockResponse("Genuine AI Output")

mock_client_instance = MockGenAIClient("user-custom-key")
with mock.patch("modules.ai_layer.client.genai.Client", return_value=mock_client_instance):
    res = c._chat(system="sys prompt", user="user prompt", json_mode=True, api_key="user-custom-key")
    assert res == "Genuine AI Output"
    assert mock_client_instance.called_model == "gemini-2.5-flash"
    assert mock_client_instance.called_contents == "user prompt"
    assert mock_client_instance.called_config.system_instruction == "sys prompt"
    assert mock_client_instance.called_config.response_mime_type == "application/json"
print("Test 12 Passed: _chat genai.Client invocation parameters")

# Test 13: Rate limiting check in _chat
t0 = time.time()
c._last_call_time = t0 - 0.5  # 0.5s ago, min interval is 2.0s
with mock.patch("modules.ai_layer.client.genai.Client", return_value=mock_client_instance):
    c._chat("sys", "user", api_key="k")
    elapsed = time.time() - t0
    assert elapsed >= 1.4, f"Rate limit delay failed: elapsed={elapsed}"
print(f"Test 13 Passed: _chat rate limiting enforced ({elapsed:.2f}s sleep)")

print("=== ALL 13 FORENSIC TESTS PASSED SUCCESSFULLY! ===")
