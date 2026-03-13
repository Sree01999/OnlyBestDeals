import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), 'state.json')

def load_state():
    """Load the state from the JSON file."""
    if not os.path.exists(STATE_FILE):
        return {"posted_deals": []}
    
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state file: {e}")
        return {"posted_deals": []}

def save_state(state):
    """Save the state to the JSON file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save state file: {e}")

def get_deal_id(deal):
    """
    Extract a unique ID from the Slickdeals link.
    Example: https://slickdeals.net/f/1234567-headline -> 1234567
    """
    import re
    link = deal.get('link', '')
    match = re.search(r'/f/(\d+)', link)
    if match:
        return match.group(1)
    return link  # Fallback to the link itself if no ID found

def filter_new_deals(deals, state):
    """
    Filter out deals that have already been posted according to the state.
    Returns a list of unique, unposted deals.
    """
    posted_ids = {item['id'] for item in state.get('posted_deals', [])}
    new_deals = []
    
    for deal in deals:
        deal_id = get_deal_id(deal)
        if deal_id not in posted_ids:
            deal['id'] = deal_id  # Attach ID for later use
            new_deals.append(deal)
        else:
            logger.info(f"Skipping already posted deal: {deal['title'][:50]}")
            
    return new_deals

def update_state(state, sent_deals, max_age_days=7):
    """
    Add new deal IDs to the state and remove old ones.
    """
    now = datetime.now()
    expiry_date = now - timedelta(days=max_age_days)
    
    # Add new deals
    for deal in sent_deals:
        state['posted_deals'].append({
            "id": deal.get('id', get_deal_id(deal)),
            "date": now.isoformat()
        })
        
    # Prune old deals
    new_posted_deals = []
    for item in state['posted_deals']:
        try:
            item_date = datetime.fromisoformat(item['date'])
            if item_date > expiry_date:
                new_posted_deals.append(item)
        except (ValueError, KeyError):
            # If date is invalid, keep it for one more run just in case
            new_posted_deals.append(item)
            
    state['posted_deals'] = new_posted_deals
    return state
