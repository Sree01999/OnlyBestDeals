# bot/fetch_deals.py
# Fetches the Slickdeals RSS feed and returns a list of deal objects.
 
import requests
from bs4 import BeautifulSoup
import logging
 
# Set up logging — all log messages go to GitHub Actions console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
 
 
# The RSS feed URLs — we use frontpage for only the best/hottest deals
RSS_URLS = {
    'frontpage':  'https://slickdeals.net/rss.php?src=frontpage',
    'all_deals':  'https://slickdeals.net/rss.php',
    'electronics':'https://slickdeals.net/rss.php?ftype=9',
}
 
 
def fetch_deals(feed='frontpage', max_deals=5):
    """
    Fetch deals from Slickdeals RSS.
 
    Args:
        feed (str): Which feed to use. Options: 'frontpage', 'all_deals', 'electronics'
        max_deals (int): How many deals to return. Default 5.
 
    Returns:
        list: List of deal dicts, or empty list on failure.
    """
    url = RSS_URLS.get(feed, RSS_URLS['frontpage'])
    logger.info(f'Fetching deals from: {url}')
 
    # ── Step 1: Make the HTTP request ──────────────────────────────
    try:
        response = requests.get(
            url,
            timeout=15,          # Wait max 15 seconds for response
            headers={
                # Identify ourselves politely — some sites block empty User-Agent
                'User-Agent': 'DealsBotRSS/1.0 (Telegram Deal Poster)'
            }
        )
        response.raise_for_status()  # Raises exception if status code is 4xx/5xx
        logger.info(f'RSS fetch successful. Status: {response.status_code}')
 
    except requests.exceptions.Timeout:
        logger.error('RSS fetch timed out after 15 seconds')
        return []
 
    except requests.exceptions.ConnectionError as e:
        logger.error(f'Network error fetching RSS: {e}')
        return []
 
    except requests.exceptions.HTTPError as e:
        logger.error(f'HTTP error from Slickdeals: {e}')
        return []
 
    # ── Step 2: Parse the XML response ─────────────────────────────
    try:
        # lxml parser is fastest for XML; html.parser is fallback
        soup = BeautifulSoup(response.content, 'lxml-xml')
    except Exception as e:
        logger.error(f'XML parsing failed: {e}')
        # Fallback: try html.parser
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
        except Exception as e2:
            logger.error(f'Fallback parsing also failed: {e2}')
            return []
 
    # ── Step 3: Extract deal items ──────────────────────────────────
    items = soup.find_all('item')  # Each <item> in the RSS = one deal
    logger.info(f'Found {len(items)} items in RSS feed')
 
    if not items:
        logger.warning('No items found in RSS — feed may have changed format')
        return []
 
    # ── Step 4: Parse each deal into a clean dictionary ────────────
    deals = []
    for item in items:  # Process all items first, so we can sort them, then slice
        try:
            deal = _parse_item(item)
            if deal:  # _parse_item returns None if item is invalid
                deals.append(deal)
                logger.info(f'  Parsed deal: {deal["title"][:60]}...')
        except Exception as e:
            logger.warning(f'Failed to parse one item, skipping: {e}')
            continue  # Skip bad items, don't crash the whole run
            
    # ── Step 5: Filter and Sort by Discounts and Ratings (User Request) ──
    deals = _filter_and_sort_deals(deals)
 
    logger.info(f'Successfully parsed and sorted {len(deals)} deals')
    return deals[:max_deals]
 
def _filter_and_sort_deals(deals):
    """
    Score and sort deals based on their title and description text using Regex.
    Looks for high discounts (e.g. 50% off) and high ratings (e.g. 4.5 stars, highly rated).
    Sorts descending based on score.
    """
    import re
    
    for deal in deals:
        score = 0
        text_to_search = (deal['title'] + " " + deal['description']).lower()
        
        # 1. Look for discounts (e.g., '50%', 'save 60%', '60% off')
        # We find all percentages and take the max as a proxy for the discount
        percentages = re.findall(r'(\d{1,2})%', text_to_search)
        if percentages:
            # Add the highest percentage found to the score (up to 99)
            max_percent = max([int(p) for p in percentages])
            score += max_percent
            
        # 2. Look for high star ratings (e.g., '4.5 stars', '4.8/5', '5 star')
        # Match pattern: 4.x or 5.0 followed by star or /5
        star_match = re.search(r'([45](?:\.\d)?)\s*(?:stars?|/5)', text_to_search)
        if star_match:
            rating = float(star_match.group(1))
            # Boost score heavily for a high rating (e.g., 4.5 * 10 = 45 points)
            score += int(rating * 10)
            
        # 3. Look for keyword indicators of good ratings
        if 'highly rated' in text_to_search or 'great reviews' in text_to_search:
            score += 20
            
        # 4. Look for massive review counts (e.g., '10,000+ reviews')
        if re.search(r'\d{1,3}(?:,\d{3})+\s*(?:\+)?\s*reviews?', text_to_search):
            score += 15
            
        deal['score'] = score
        
    # Sort deals by highest score first
    deals.sort(key=lambda d: d.get('score', 0), reverse=True)
    return deals
 
 
def _parse_item(item):
    """
    Parse a single RSS <item> element into a deal dictionary.
    Returns None if the item doesn't have the minimum required fields.
    """
    # Extract title — required field
    title_tag = item.find('title')
    if not title_tag or not title_tag.text.strip():
        return None  # Skip items with no title
 
    title = title_tag.text.strip()
 
    # Extract link — required field
    link_tag = item.find('link')
    link = link_tag.text.strip() if link_tag else ''
 
    # Extract description — optional, used for price/store info
    desc_tag = item.find('description')
    description = ''
    if desc_tag and desc_tag.text:
        # Description often contains HTML — strip tags for clean text
        desc_soup = BeautifulSoup(desc_tag.text, 'html.parser')
        description = desc_soup.get_text(separator=' ').strip()[:300]
 
    # Extract image URL — optional, used for Telegram photo messages
    image_url = _extract_image(item, desc_tag)
 
    # Extract publication date — optional, used for context
    pub_date_tag = item.find('pubDate')
    pub_date = pub_date_tag.text.strip() if pub_date_tag else ''
 
    # Extract category — optional, used for emoji selection
    category_tag = item.find('category')
    category = category_tag.text.strip() if category_tag else 'General'
 
    return {
        'title':       title,
        'link':        link,
        'description': description,
        'image_url':   image_url,
        'pub_date':    pub_date,
        'category':    category,
    }
 
 
def _extract_image(item, desc_tag):
    """
    Try to find an image URL from the RSS item.
    Slickdeals sometimes includes images in <enclosure> or inside the description HTML.
    Returns empty string if no image found.
    """
    # Try <enclosure url='...' type='image/...'>
    enclosure = item.find('enclosure')
    if enclosure and enclosure.get('type', '').startswith('image'):
        return enclosure.get('url', '')
 
    # Try <media:content> tag
    media = item.find('media:content')
    if media and media.get('url'):
        return media.get('url')
 
    # Try finding <img src='...'> inside the description HTML
    if desc_tag and desc_tag.text:
        desc_soup = BeautifulSoup(desc_tag.text, 'html.parser')
        img_tag = desc_soup.find('img')
        if img_tag and img_tag.get('src'):
            src = img_tag.get('src')
            # Only return absolute URLs (starting with http)
            if src.startswith('http'):
                return src
 
    return ''  # No image found
