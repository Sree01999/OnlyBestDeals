# bot/send_telegram.py
# Sends messages to a Telegram channel via the Telegram Bot API.
# Handles both text messages and photo messages (when image URL is available).
 
import requests
import time
import logging
 
logger = logging.getLogger(__name__)
 
# Telegram Bot API base URL
# Your bot token is injected via environment variable — never hardcoded
TELEGRAM_API = 'https://api.telegram.org/bot{token}/{method}'
 
# How long to wait between sends to avoid hitting Telegram rate limits
# Telegram allows 30 messages per second, but for channels 1 msg/sec is safe
SEND_DELAY_SECONDS = 1.5
 
# How many times to retry a failed send before giving up
MAX_RETRIES = 3
 
# How long to wait before retrying (seconds)
RETRY_DELAY_SECONDS = 5
 
 
def _make_api_url(bot_token, method):
    """Build the full Telegram API URL for a given method."""
    return TELEGRAM_API.format(token=bot_token, method=method)
 
 
def send_text_message(bot_token, channel_id, text, disable_preview=False):
    """
    Send a text message (with HTML formatting) to the Telegram channel.
 
    Args:
        bot_token (str):   Your Telegram Bot Token
        channel_id (str):  Your channel ID or @username
        text (str):        The message text (HTML formatted)
        disable_preview (bool): Whether to disable link previews
 
    Returns:
        bool: True if sent successfully, False if all retries failed
    """
    url = _make_api_url(bot_token, 'sendMessage')
    payload = {
        'chat_id':                  channel_id,
        'text':                     text,
        'parse_mode':               'HTML',       # Enable HTML formatting
        'disable_web_page_preview': disable_preview,
    }
 
    return _send_with_retry(url, payload, message_type='text')
 
 
def send_photo_message(bot_token, channel_id, photo_url, caption):
    """
    Send a photo message with a caption to the Telegram channel.
    Used when a deal has an image URL available.
 
    Args:
        bot_token (str):  Your Telegram Bot Token
        channel_id (str): Your channel ID or @username
        photo_url (str):  Public URL of the product image
        caption (str):    Message text shown below the photo (HTML formatted)
 
    Returns:
        bool: True if sent successfully, False if all retries failed
    """
    url = _make_api_url(bot_token, 'sendPhoto')
    payload = {
        'chat_id':    channel_id,
        'photo':      photo_url,
        'caption':    caption,  # Length should be checked beforehand
        'parse_mode': 'HTML',
    }
 
    return _send_with_retry(url, payload, message_type='photo')
 
 
def _send_with_retry(url, payload, message_type='text'):
    """
    Internal function: send request to Telegram API with retry logic.
    Retries up to MAX_RETRIES times on failure before giving up.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f'Sending {message_type} message (attempt {attempt}/{MAX_RETRIES})')
 
            response = requests.post(
                url,
                json=payload,
                timeout=10  # Wait max 10 seconds for Telegram to respond
            )
 
            # Parse the response
            result = response.json()
 
            if result.get('ok'):
                logger.info(f'{message_type.capitalize()} message sent successfully')
                return True
 
            else:
                # Telegram returned an error code
                error_code = result.get('error_code', 'unknown')
                description = result.get('description', 'no description')
                logger.error(f'Telegram API error {error_code}: {description}')
 
                # 429 = Too Many Requests — wait longer before retry
                if error_code == 429:
                    retry_after = result.get('parameters', {}).get('retry_after', 30)
                    logger.info(f'Rate limited. Waiting {retry_after} seconds...')
                    time.sleep(retry_after)
                else:
                    # Non-rate-limit error — wait standard delay
                    if attempt < MAX_RETRIES:
                        logger.info(f'Retrying in {RETRY_DELAY_SECONDS}s...')
                        time.sleep(RETRY_DELAY_SECONDS)
 
        except requests.exceptions.Timeout:
            logger.warning(f'Telegram request timed out (attempt {attempt})')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
 
        except requests.exceptions.ConnectionError as e:
            logger.warning(f'Connection error to Telegram (attempt {attempt}): {e}')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
 
        except Exception as e:
            logger.error(f'Unexpected error sending message: {e}')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
 
    logger.error(f'All {MAX_RETRIES} attempts failed for {message_type} message')
    return False
 
 
def send_deal(bot_token, channel_id, deal, formatted_message):
    """
    High-level function: sends one deal to the channel.
    Tries to send as a photo message first (if image available),
    falls back to text message if no image or if photo send fails.
 
    Args:
        bot_token (str):         Bot token
        channel_id (str):        Channel ID
        deal (dict):             Deal object from fetch_deals.py
        formatted_message (str): Pre-formatted HTML text from format_message.py
 
    Returns:
        bool: True if deal was sent (via any method), False if all methods failed
    """
    image_url = deal.get('image_url', '')
 
    # Try photo message if image is available
    if image_url:
        logger.info('Deal has image — attempting sendPhoto')
        # Telegram photo captions are limited to 1024 chars.
        # If the formatted message is too long, we shouldn't arbitrarily slice it,
        # as that could break HTML tags. Just use a text message fallback instead.
        if len(formatted_message) <= 1024:
            success = send_photo_message(bot_token, channel_id, image_url, formatted_message)
            if success:
                return True
            logger.warning('Photo send failed — falling back to text message')
        else:
            logger.info('Message exceeds photo caption limit (1024 chars). Sending as text message instead.')
 
    # Send as plain text message (no image)
    return send_text_message(bot_token, channel_id, formatted_message)
