import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.fetch_deals import _parse_item, _extract_image
from bs4 import BeautifulSoup

def test_parse_item_missing_title():
    xml = "<item><link>http://example.com</link></item>"
    soup = BeautifulSoup(xml, 'xml')
    item = soup.find('item')
    assert _parse_item(item) is None

def test_parse_item_valid():
    xml = """
    <item>
        <title>Great Deal</title>
        <link>http://example.com</link>
        <description>Some HTML description &lt;img src="http://example.com/img.jpg" /&gt;</description>
        <pubDate>Mon, 01 Jan 2024</pubDate>
        <category>Electronics</category>
    </item>
    """
    soup = BeautifulSoup(xml, 'xml')
    item = soup.find('item')
    deal = _parse_item(item)
    
    assert deal is not None
    assert deal['title'] == 'Great Deal'
    assert deal['link'] == 'http://example.com'
    assert deal['description'].startswith('Some HTML')
    assert deal['image_url'] == 'http://example.com/img.jpg'
    assert deal['pub_date'] == 'Mon, 01 Jan 2024'
    assert deal['category'] == 'Electronics'

def test_extract_image_enclosure():
    xml = "<item><enclosure url='http://example.com/enclosure.jpg' type='image/jpeg' /></item>"
    soup = BeautifulSoup(xml, 'xml')
    item = soup.find('item')
    assert _extract_image(item, None) == 'http://example.com/enclosure.jpg'

def test_filter_and_sort_deals():
    from bot.fetch_deals import _filter_and_sort_deals
    
    deals = [
        {"title": "Boring Item", "description": "Just a normal item."},
        {"title": "Great TV 50% off", "description": "Save big! 4.5 stars and highly rated."},
        {"title": "Phone Case", "description": "Cheap case, 10% discount."},
        {"title": "Awesome Headphones", "description": "Over 10,000 reviews and 4.8/5 rating. 20% off."},
    ]
    
    sorted_deals = _filter_and_sort_deals(deals)
    
    # TV should be #1 (50 + 45 + 20 = 115 points)
    assert sorted_deals[0]["title"] == "Great TV 50% off"
    
    # Headphones should be #2 (20 + 48 + 15 = 83 points)
    assert sorted_deals[1]["title"] == "Awesome Headphones"
    
    # Phone case should be #3 (10 points)
    assert sorted_deals[2]["title"] == "Phone Case"
    
    # Boring item should be last (0 points)
    assert sorted_deals[3]["title"] == "Boring Item"
