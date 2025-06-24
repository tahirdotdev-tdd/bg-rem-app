#!/usr/bin/env python3
import requests
import base64
import json
import time
import os
from PIL import Image
import io
import unittest

# Get the backend URL from the frontend .env file
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.strip().split('=')[1].strip('"')
            break

# Ensure the URL doesn't have quotes
BACKEND_URL = BACKEND_URL.strip("'\"")
API_URL = f"{BACKEND_URL}/api"

print(f"Using API URL: {API_URL}")

# Create a test image in memory
def create_test_image():
    # Create a simple test image (100x100 red square)
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()

# Convert bytes to base64
def bytes_to_base64(img_bytes):
    return base64.b64encode(img_bytes).decode('utf-8')

class BackgroundRemovalAPITest(unittest.TestCase):
    
    def setUp(self):
        self.test_image_bytes = create_test_image()
        self.test_image_base64 = bytes_to_base64(self.test_image_bytes)
    
    def test_health_check(self):
        """Test the API health check endpoint"""
        print("\n1. Testing API health check...")
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Background Removal API Ready")
        print("✅ Health check passed")
    
    def test_background_removal(self):
        """Test the background removal endpoint with valid image"""
        print("\n2. Testing background removal with valid image...")
        payload = {
            "image_data": self.test_image_base64,
            "filename": "test_image.png"
        }
        
        response = requests.post(f"{API_URL}/remove-background", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["processed_image"])
        self.assertIsNotNone(data["processing_time"])
        
        # Verify the processed image is valid base64
        try:
            processed_bytes = base64.b64decode(data["processed_image"])
            processed_img = Image.open(io.BytesIO(processed_bytes))
            # Verify it's a PNG with alpha channel (RGBA)
            self.assertEqual(processed_img.mode, "RGBA")
        except Exception as e:
            self.fail(f"Processed image is not valid: {str(e)}")
        
        print(f"✅ Background removal successful. Processing time: {data['processing_time']:.2f}s")
    
    def test_invalid_image_data(self):
        """Test the background removal endpoint with invalid base64 data"""
        print("\n3. Testing background removal with invalid image data...")
        payload = {
            "image_data": "invalid_base64_data",
            "filename": "test_image.png"
        }
        
        response = requests.post(f"{API_URL}/remove-background", json=payload)
        # Should either return 400 or success=False
        if response.status_code == 400:
            print("✅ Server correctly rejected invalid image with 400 status")
        else:
            data = response.json()
            self.assertFalse(data["success"])
            self.assertIsNotNone(data["error"])
            print(f"✅ Server handled invalid image. Error: {data['error']}")
    
    def test_upload_image(self):
        """Test the file upload endpoint"""
        print("\n4. Testing file upload endpoint...")
        files = {
            'file': ('test_image.png', self.test_image_bytes, 'image/png')
        }
        
        response = requests.post(f"{API_URL}/upload-image", files=files)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["filename"], "test_image.png")
        self.assertEqual(data["content_type"], "image/png")
        self.assertIsNotNone(data["image_data"])
        
        # Verify the returned image data is valid base64
        try:
            returned_bytes = base64.b64decode(data["image_data"])
            self.assertEqual(returned_bytes, self.test_image_bytes)
        except Exception as e:
            self.fail(f"Returned image data is not valid: {str(e)}")
        
        print("✅ File upload successful")
    
    def test_invalid_file_upload(self):
        """Test the file upload endpoint with invalid file type"""
        print("\n5. Testing file upload with invalid file type...")
        # Create a text file instead of an image
        text_bytes = b"This is not an image"
        
        files = {
            'file': ('test.txt', text_bytes, 'text/plain')
        }
        
        response = requests.post(f"{API_URL}/upload-image", files=files)
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertEqual(data["detail"], "File must be an image")
        
        print("✅ Server correctly rejected non-image file")

if __name__ == "__main__":
    print("Starting Background Removal API Tests")
    print(f"API URL: {API_URL}")
    
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)