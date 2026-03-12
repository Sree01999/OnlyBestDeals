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
