def test_get_cv_events_empty(client, auth_headers):
    response = client.get("/cv/events", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_voice_speak(client):
    response = client.post("/voice/speak", json={"text": "Hello"})
    # It returns 202 accepted and kicks off a background task
    assert response.status_code == 200
    assert response.json() == {"ok": True, "spoken": "Hello"}
