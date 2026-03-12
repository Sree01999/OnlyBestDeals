# bot/main.py
# Entry point for the Deals Bot.
# GitHub Actions runs: python bot/main.py
 
import os
import sys
import logging
import time
 
from fetch_deals   import fetch_deals
from format_message import format_deal_message, format_header_message, format_footer_message
from send_telegram  import send_text_message, send_deal
 
# ── Logging setup ────────────────────────────────────────────────────
# All output goes to GitHub Actions console — visible in the workflow logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('main')
 
 
# ── Configuration ────────────────────────────────────────────────────
# These values come from GitHub Actions Secrets (never hardcoded here)
BOT_TOKEN  = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
 
# How many deals to post each morning (change this to your preference)
MAX_DEALS = int(os.environ.get('MAX_DEALS', '50'))
 
# Which Slickdeals feed to use: 'frontpage', 'all_deals', or 'electronics'
FEED_TYPE = os.environ.get('FEED_TYPE', 'frontpage')
 
# Delay between sending each deal message (seconds) — avoids rate limits
MESSAGE_DELAY = float(os.environ.get('MESSAGE_DELAY', '2.0'))
 
 
def validate_config():
    """
    Check that required environment variables are set.
    Exit immediately if they're missing — no point running without credentials.
    """
    errors = []
 
    if not BOT_TOKEN:
        errors.append('TELEGRAM_BOT_TOKEN is not set')
    elif not BOT_TOKEN.count(':') == 1:
        errors.append('TELEGRAM_BOT_TOKEN format looks wrong (expected format: 123456:ABC-xxx)')
 
    if not CHANNEL_ID:
        errors.append('TELEGRAM_CHANNEL_ID is not set')
 
    if errors:
        for err in errors:
            logger.error(f'CONFIG ERROR: {err}')
        logger.error('Fix the above secrets in GitHub → Settings → Secrets and Variables → Actions')
        sys.exit(1)  # Exit code 1 = failure — GitHub Actions will mark run as FAILED
 
    logger.info(f'Config OK — Channel: {CHANNEL_ID} | Max deals: {MAX_DEALS} | Feed: {FEED_TYPE}')
 
 
def run():
    """
    Main execution function.
    Flow: validate → fetch → send header → send deals → send footer → exit
    """
    logger.info('=' * 60)
    logger.info('DEALS BOT STARTING')
    logger.info('=' * 60)
 
    # ── Step 1: Validate config ────────────────────────────────────
    validate_config()
 
    # ── Step 2: Fetch deals ────────────────────────────────────────
    logger.info(f'Fetching top {MAX_DEALS} deals from {FEED_TYPE} feed...')
    deals = fetch_deals(feed=FEED_TYPE, max_deals=MAX_DEALS)
 
    if not deals:
        logger.error('No deals fetched — aborting run')
        # Send a failure notification to the channel so you know something went wrong
        send_text_message(
            BOT_TOKEN, CHANNEL_ID,
            '⚠️ <b>Deals Bot Error</b>\n\nCould not fetch deals today. Will retry tomorrow.'
        )
        sys.exit(1)
 
    logger.info(f'Fetched {len(deals)} deals successfully')
 
    # ── Step 3: Send header message ───────────────────────────────
    logger.info('Sending header message...')
    header = format_header_message(len(deals))
    header_sent = send_text_message(BOT_TOKEN, CHANNEL_ID, header, disable_preview=True)
 
    if not header_sent:
        logger.error('Failed to send header message — check bot token and channel ID')
        sys.exit(1)
 
    time.sleep(MESSAGE_DELAY)
 
    # ── Step 4: Send each deal ────────────────────────────────────
    sent_count    = 0
    failed_count  = 0
 
    for i, deal in enumerate(deals, start=1):
        logger.info(f'Sending deal {i}/{len(deals)}: {deal["title"][:50]}')
 
        # Format the message
        message = format_deal_message(deal, deal_number=i, total_deals=len(deals))
 
        # Send it
        success = send_deal(BOT_TOKEN, CHANNEL_ID, deal, message)
 
        if success:
            sent_count += 1
        else:
            failed_count += 1
            logger.warning(f'Failed to send deal {i} — continuing with next deal')
 
        # Wait between messages to respect Telegram rate limits
        if i < len(deals):
            time.sleep(MESSAGE_DELAY)
 
    # ── Step 5: Send footer message ───────────────────────────────
    logger.info('Sending footer message...')
    time.sleep(MESSAGE_DELAY)
    footer = format_footer_message()
    send_text_message(BOT_TOKEN, CHANNEL_ID, footer, disable_preview=True)
 
    # ── Step 6: Final summary ──────────────────────────────────────
    logger.info('=' * 60)
    logger.info(f'RUN COMPLETE — Sent: {sent_count} | Failed: {failed_count}')
    logger.info('=' * 60)
 
    # Exit with failure code if any deals failed to send
    if failed_count > 0 and sent_count == 0:
        logger.error('All sends failed — marking run as FAILED')
        sys.exit(1)
 
    # Partial success is still OK — exit 0
    sys.exit(0)
 
 
if __name__ == '__main__':
    run()
