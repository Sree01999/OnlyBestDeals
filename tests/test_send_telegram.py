import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.send_telegram import send_text_message, send_photo_message, send_deal

def test_send_text_message(mocker):
    mock_post = mocker.patch('requests.post')
    mock_post.return_value.json.return_value = {'ok': True}
    
    result = send_text_message('fake:token', '@fakechannel', '<b>Hello</b>')
    
    assert result is True
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]['json']
    assert payload['chat_id'] == '@fakechannel'
    assert payload['text'] == '<b>Hello</b>'
    assert payload['parse_mode'] == 'HTML'

def test_send_photo_message_with_long_caption(mocker):
    mock_post = mocker.patch('requests.post')
    mock_post.return_value.json.return_value = {'ok': True}
    
    long_caption = "A" * 2000
    result = send_photo_message('fake:token', '@fakechannel', 'http://example.com/img.jpg', long_caption)
    
    assert result is True
    payload = mock_post.call_args[1]['json']
    assert len(payload['caption']) == 1024 # Note: This will be fixed in the following steps

def test_send_deal_success_fallback(mocker):
    # Mock send_photo to fail, text to succeed
    mocker.patch('bot.send_telegram.send_photo_message', return_value=False)
    mock_send_text = mocker.patch('bot.send_telegram.send_text_message', return_value=True)
    
    deal = {'image_url': 'http://example.com/img.jpg'}
    result = send_deal('fake:token', '@fakechannel', deal, '<b>Message</b>')
    
    assert result is True
    mock_send_text.assert_called_once_with('fake:token', '@fakechannel', '<b>Message</b>')
