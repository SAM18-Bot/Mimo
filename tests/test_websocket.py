import pytest
from fastapi.testclient import TestClient
from main import app

def test_websocket_missing_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            pass

def test_websocket_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid_jwt") as ws:
            pass

def test_websocket_dev_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=dev_token") as ws:
            pass
