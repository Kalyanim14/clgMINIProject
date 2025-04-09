import pytest
from flask import Flask, url_for
from unittest.mock import patch, MagicMock
import os
import cv2
import mysql.connector
from io import BytesIO
import uuid

# Import your app (make sure this matches your Flask app filename)
from app import app, encrypt_message, decrypt_message, allowed_file

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = 'test_uploads'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file))
    os.rmdir(app.config['UPLOAD_FOLDER'])

def test_allowed_file():
    assert allowed_file('test.jpg') is True
    assert allowed_file('test.png') is True
    assert allowed_file('test.txt') is False

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    # Test if your main page loads with correct HTML
    assert b'<html' in response.data
    assert b'<head' in response.data
    assert b'<body' in response.data

def test_encrypt_route_get(client):
    response = client.get('/encrypt')
    assert response.status_code == 200
    # Test if form exists
    assert b'<form' in response.data
    assert b'type="file"' in response.data
    assert b'type="password"' in response.data

@patch('mysql.connector.connect')
def test_encrypt_route_post(mock_db, client):
    # Setup mock database
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Create test image
    test_image = (BytesIO(b'fake image data'), 'test.png')
    
    response = client.post('/encrypt', data={
        'image': test_image,
        'message': 'secret',
        'password': 'mypassword'
    }, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200
    # Test if success message appears in HTML
    assert b'success' in response.data.lower()
    assert b'download' in response.data.lower()  # Check for download link

def test_decrypt_route_get(client):
    response = client.get('/decrypt')
    assert response.status_code == 200
    # Test if decrypt form exists
    assert b'<form' in response.data
    assert b'type="file"' in response.data
    assert b'type="password"' in response.data

@patch('mysql.connector.connect')
def test_decrypt_route_post(mock_db, client):
    # Setup mock database
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = ('correct_password',)
    
    test_image = (BytesIO(b'fake image data'), 'encrypted_test.png')
    
    with patch('app.decrypt_message') as mock_decrypt:
        mock_decrypt.return_value = "decrypted message"
        response = client.post('/decrypt', data={
            'image': test_image,
            'password': 'correct_password',
            'image_id': str(uuid.uuid4())
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert response.status_code == 200
        # Test if decrypted message appears in HTML
        assert b'decrypted message' in response.data

def test_static_files(client):
    """Test that static files (CSS/JS) are properly served"""
    # Test CSS file
    css_response = client.get('/static/style.css')
    assert css_response.status_code == 200
    assert 'text/css' in css_response.headers['Content-Type'].lower()
