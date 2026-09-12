import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app  # Import your FastAPI app

# from app.api.routes.line import parser, configuration  # Correct import for parser and configuration
from linebot.v3.exceptions import InvalidSignatureError
from app.core.config import settings

client = TestClient(app)


@pytest.mark.asyncio
async def test_valid_callback():
    # Mock valid Line request data
    body = '{"events":[{"type":"message","message":{"type":"text","text":"Hello"},"replyToken":"validToken"}]}'
    signature = "valid_signature"

    # Mock the parser and line_bot_api.reply_message
    with patch("app.api.routes.line.parser.parse") as mock_parser, patch(
        "linebot.v3.messaging.AsyncMessagingApi.reply_message"
    ) as mock_reply_message:
        # Mock parser behavior
        mock_parser.return_value = [
            AsyncMock(
                message=AsyncMock(text="Hello"),
                reply_token="validToken",
                __class__=AsyncMock,
            )
        ]

        # Mock reply_message behavior
        mock_reply_message.return_value = AsyncMock()

        # Send POST request to the /callback route
        response = client.post(
            f"{settings.API_V1_STR}/line/callback",
            headers={"X-Line-Signature": signature},
            data=body,
        )

        # Assertions
        assert response.status_code == 200
        assert response.text == '"OK"'
        mock_parser.assert_called_once_with(body, signature)

        # this could never be tested locally, because reply
        # is from line server.
        # mock_reply_message.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_signature():
    # Mock invalid Line request data
    body = '{"events":[]}'
    invalid_signature = "invalid_signature"

    # Mock the parser to raise InvalidSignatureError
    with patch("app.api.routes.line.parser.parse", side_effect=InvalidSignatureError):
        response = client.post(
            f"{settings.API_V1_STR}/line/callback",
            headers={"X-Line-Signature": invalid_signature},
            data=body,
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid signature"


@pytest.mark.asyncio
async def test_non_message_event():
    # Mock Line request data with non-message event
    body = '{"events":[{"type":"follow","replyToken":"dummyToken"}]}'
    signature = "valid_signature"

    # Mock the parser
    with patch("app.api.routes.line.parser.parse") as mock_parser:
        mock_parser.return_value = [
            AsyncMock(type="follow", reply_token="dummyToken", __class__=AsyncMock)
        ]

        # Send POST request to the /callback route
        response = client.post(
            f"{settings.API_V1_STR}/line/callback",
            headers={"X-Line-Signature": signature},
            data=body,
        )

        # Assertions
        assert response.status_code == 200
        assert response.text == '"OK"'


@pytest.mark.asyncio
async def test_non_text_message():
    # Mock Line request data with non-text message
    body = '{"events":[{"type":"message","message":{"type":"image"},"replyToken":"dummyToken"}]}'
    signature = "valid_signature"

    # Mock the parser
    with patch("app.api.routes.line.parser.parse") as mock_parser:
        mock_parser.return_value = [
            AsyncMock(
                message=AsyncMock(type="image"),
                reply_token="dummyToken",
                __class__=AsyncMock,
            )
        ]

        # Send POST request to the /callback route
        response = client.post(
            f"{settings.API_V1_STR}/line/callback",
            headers={"X-Line-Signature": signature},
            data=body,
        )

        # Assertions
        assert response.status_code == 200
        assert response.text == '"OK"'
