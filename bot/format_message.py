# bot/format_message.py
# Formats a deal dictionary into a Telegram-ready HTML message.
 
import html
import logging
 
logger = logging.getLogger(__name__)
 
 
# Emoji map — assigns an emoji based on deal category keyword
CATEGORY_EMOJIS = {
    'electronics':   '🖥️',
    'computer':      '💻',
    'phone':         '📱',
    'laptop':        '💻',
    'tv':            '📺',
    'gaming':        '🎮',
    'clothing':      '👕',
    'fashion':       '👗',
    'shoes':         '👟',
    'grocery':       '🛒',
    'food':          '🍔',
    'kitchen':       '🍳',
    'home':          '🏠',
    'garden':        '🌿',
    'baby':          '👶',
    'toy':           '🧸',
    'book':          '📚',
    'sport':         '⚽',
    'fitness':       '💪',
    'travel':        '✈️',
    'auto':          '🚗',
    'health':        '💊',
    'beauty':        '💄',
    'pet':           '🐾',
    'software':      '💿',
    'subscription':  '🔁',
    'free':          '🆓',
}
 
DEFAULT_EMOJI = '🔥'  # Used when no category match found
 
 
def get_emoji(deal):
    """
    Pick the best emoji for a deal based on its title and category.
    Checks both title and category text for keyword matches.
    """
    text_to_check = (deal['title'] + ' ' + deal['category']).lower()
 
    for keyword, emoji in CATEGORY_EMOJIS.items():
        if keyword in text_to_check:
            return emoji
 
    return DEFAULT_EMOJI
 
 
def escape_html(text):
    """
    Telegram HTML mode requires escaping <, >, & characters.
    This prevents formatting errors when deal titles contain those chars.
    """
    return html.escape(str(text))
 
 
def format_deal_message(deal, deal_number=None, total_deals=None):
    """
    Format a single deal into a Telegram HTML message string.
 
    Args:
        deal (dict): Deal dict from fetch_deals.py
        deal_number (int): Optional — deal index for 'Deal 1 of 5' header
        total_deals (int): Optional — total count for header
 
    Returns:
        str: Formatted HTML string ready for Telegram API
    """
    emoji   = get_emoji(deal)
    title   = escape_html(deal['title'])
    link    = deal['link']
    desc    = escape_html(deal['description'][:200]) if deal['description'] else ''
    category= escape_html(deal['category'])
 
    # ── Build the message ────────────────────────────────────────────
    lines = []
 
    # Header line with emoji and counter
    if deal_number and total_deals:
        lines.append(f'{emoji} <b>Deal {deal_number} of {total_deals}</b>')
    else:
        lines.append(f'{emoji} <b>Hot Deal</b>')
 
    lines.append('')  # Blank line for spacing
 
    # Title as a clickable link
    lines.append(f'<b><a href="{link}">{title}</a></b>')
 
    lines.append('')  # Blank line
 
    # Description (if available)
    if desc:
        lines.append(f'📝 {desc}')
        lines.append('')
 
    # Category badge
    lines.append(f'🏷️ <i>{category}</i>')
 
    lines.append('')
 
    # Action button row
    lines.append(f'👉 <a href="{link}">View Deal on Slickdeals</a>')
 
    lines.append('')
    lines.append('─' * 30)  # Visual separator between deals
 
    message = '\n'.join(lines)
 
    logger.info(f'Formatted message for: {deal["title"][:50]}...')
    return message
 
 
def format_header_message(deal_count):
    """
    Creates the introductory message sent before the individual deals.
    This appears first in your Telegram channel as a 'good morning' header.
    """
    from datetime import datetime
    today = datetime.now().strftime('%A, %B %d %Y')  # e.g. 'Monday, January 15 2025'
 
    return (
        f'🌅 <b>Good Morning! Daily Deals — {today}</b>\n'
        f'\n'
        f"Here are today's top <b>{deal_count} deals</b> from Slickdeals 🛍️\n"
        f'\n'
        f'All deals are community-verified. Prices change fast — act quickly! ⚡'
    )
 
 
def format_footer_message():
    """
    Creates a closing message sent after all deals.
    """
    return (
        '✅ <b>That is all for today!</b>\n'
        '\n'
        'See you tomorrow at 8:00 AM for fresh deals. 🔔\n'
        '\n'
        '<i>Source: Slickdeals.net — Community-verified deals</i>'
    )
