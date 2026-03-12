import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.format_message import get_emoji, escape_html, format_deal_message

def test_get_emoji():
    # Matches electronics
    assert get_emoji({'title': 'New Macbook Pro', 'category': 'Laptop'}) == '💻'
    # No match, default
    assert get_emoji({'title': 'Random Item', 'category': 'Misc'}) == '🔥'

def test_escape_html():
    assert escape_html("Macbook <15> & more") == "Macbook &lt;15&gt; &amp; more"

def test_format_deal_message():
    deal = {
        'title': 'Test <Title>',
        'link': 'http://example.com',
        'description': 'A very long description that goes on ' * 10,
        'category': 'Electronics'
    }
    
    msg = format_deal_message(deal)
    
    # Must contain escaped title
    assert 'Test &lt;Title&gt;' in msg
    assert 'http://example.com' in msg
    assert 'Electronics' in msg
    
    # Check length limits applied (description sliced to 200 before escape)
    # The actual length might vary slightly due to HTML formatting, but shouldn't exceed 1000
    assert len(msg) < 1000
