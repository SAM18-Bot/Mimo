def test_get_cv_events_empty(client, auth_headers):
    response = client.get("/cv/events", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_voice_speak(client, auth_headers):
    response = client.post("/voice/speak", json={"text": "Hello"}, headers=auth_headers)
    # It returns 202 accepted and kicks off a background task
    assert response.status_code == 200
    assert response.json() == {"ok": True, "spoken": "Hello"}



def test_camera_falls_back_when_mediapipe_cannot_initialize(monkeypatch):
    import sys

    import numpy as np

    from modules.cv_pipeline.presence import PresenceMonitor

    monkeypatch.setitem(sys.modules, "mediapipe", None)
    monitor = PresenceMonitor()
    try:
        assert monitor._gaze_detector is None
        assert monitor._analyze_frame(np.zeros((64, 64, 3), dtype=np.uint8)) == (False, False)
    finally:
        monitor.stop()
