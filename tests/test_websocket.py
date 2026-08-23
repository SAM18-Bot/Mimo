import pytest


def test_websocket_missing_token(client):
    with pytest.raises(Exception), client.websocket_connect("/ws"):
        pass

def test_websocket_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid_jwt"):
            pass

def test_websocket_dev_token(client):
    with pytest.raises(Exception), client.websocket_connect("/ws?token=dev_token"):
        pass


@pytest.mark.anyio
async def test_connection_manager_unicast_and_broadcast():
    from unittest.mock import AsyncMock

    from api.websocket import ConnectionManager

    cm = ConnectionManager()
    ws_user1 = AsyncMock()
    ws_user2 = AsyncMock()

    await cm.connect(ws_user1, user_id=101)
    await cm.connect(ws_user2, user_id=102)

    assert cm.client_count == 2
    assert ws_user1 in cm._user_sockets[101]
    assert ws_user2 in cm._user_sockets[102]

    # Test unicast to user 101
    await cm.unicast(101, {"type": "test_101", "user_id": 101})
    ws_user1.send_text.assert_called_once()
    ws_user2.send_text.assert_not_called()

    ws_user1.send_text.reset_mock()
    ws_user2.send_text.reset_mock()

    # Test broadcast with user_id=102
    await cm.broadcast({"type": "test_102"}, user_id=102)
    ws_user2.send_text.assert_called_once()
    ws_user1.send_text.assert_not_called()

    ws_user1.send_text.reset_mock()
    ws_user2.send_text.reset_mock()

    # Test disconnect
    cm.disconnect(ws_user1)
    assert cm.client_count == 1
    assert 101 not in cm._user_sockets


def test_websocket_valid_token(client, auth_headers):
    token = auth_headers['Authorization'].replace('Bearer ', '')
    with client.websocket_connect(f'/ws?token={token}'):
        # If it doesn\'t raise an exception, connection is successful
        pass
