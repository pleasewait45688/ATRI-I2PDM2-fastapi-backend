import sys
import logging

from fastapi import APIRouter, Request, HTTPException

from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from app.core.config import settings

logging.basicConfig(
    filename="app.log",  # Log file name
    level=logging.DEBUG,  # Set logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter()

# get channel_secret and channel_access_token from your environment variable
channel_secret = settings.LINE_CHANNEL_SECRET
channel_access_token = settings.LINE_CHANNEL_ACCESS_TOKEN
frontend_base_url = settings.FRONTEND_BASE_URL

if channel_secret is None:
    logger.error("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    logger.error("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)
if frontend_base_url is None:
    logger.error("Specify FRONTEND_BASE_URL as environment variable.")
    sys.exit(1)

configuration = Configuration(access_token=channel_access_token)


parser = WebhookParser(channel_secret)

@router.post("/callback")
async def handle_callback(request: Request):
    # Get the signature header
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.error("Missing X-Line-Signature header")
        raise HTTPException(
            status_code=400, detail="X-Line-Signature header is missing"
        )

    # Get request body as text
    body = await request.body()
    body_decoded = body.decode()

    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"Request body: {body_decoded}")

    try:
        events = parser.parse(body_decoded, signature)
        logger.debug(f"Parsed events: {events}")
    except InvalidSignatureError:
        logger.error("Invalid signature detected")
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            logger.debug(f"Skipping non-message event: {event}")
            continue
        if not isinstance(event.message, TextMessageContent):
            logger.debug(f"Skipping non-text message: {event.message}")
            continue

        async_api_client = AsyncApiClient(configuration)
        line_bot_api = AsyncMessagingApi(async_api_client)

        user_id = event.source.user_id
        user_message = event.message.text.strip()
        
        # TODO: 安全性強化：將 user_id 改成短期有效 token 綁定（以避免 userId 洩漏）
        # NOTE: 當前版本為開發階段，user_id 直接使用
        try:
            if user_message == "開發專區":
                logger.info(f"🔍 查詢用戶 userId: {user_id}")
                recognition_url = f"{frontend_base_url}/?userid={user_id}"
                info_url = f"{frontend_base_url}/info?userid={user_id}"
                history_url = f"{frontend_base_url}/history?userid={user_id}"

                logger.debug("🔗 建立功能連結完成")
                logger.debug(f"  - recognition_url = {recognition_url}")
                logger.debug(f"  - info_url        = {info_url}")
                logger.debug(f"  - history_url     = {history_url}")

                flex_contents = {
                    "type": "bubble",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "md",
                        "contents": [
                            {"type": "text", "text": "開發人員專區", "weight": "bold", "size": "xl"},
                            {"type": "text", "text": "請選擇功能：", "size": "sm", "color": "#666666"},
                            {"type": "button", "style": "primary",
                            "action": {"type": "uri", "label": "害蟲辨識", "uri": recognition_url}},
                            {"type": "button", "style": "secondary",
                            "action": {"type": "uri", "label": "基本資料", "uri": info_url}},
                            {"type": "button", "style": "secondary",
                            "action": {"type": "uri", "label": "歷史紀錄", "uri": history_url}},
                        ],
                    },
                }

                logger.debug("🧩 Flex message JSON 結構建立完成")

                flex_message = FlexMessage(
                    alt_text="害蟲辨識系統選單",
                    contents=FlexContainer.from_dict(flex_contents),
                )

                logger.info("🚀 準備回傳 Flex Message")
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[flex_message],
                    )
                )
                logger.info("✅ Flex Message 回傳成功")

            else:
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=user_message)],
                    )
                )
                logger.info(f"Replied to message: {user_message}")
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            raise HTTPException(status_code=500, detail="Failed to reply to message")
        
    return "OK"


