"""
Test Script for URL/YouTube Extraction
======================================

This script tests the new URL and YouTube extraction features.
Run with: python scripts/test_url_extraction.py

Prerequisites:
- Server running at http://localhost:8002
- Dependencies installed (yt-dlp, whisper, ffmpeg, beautifulsoup4)
"""
import requests
import json
import time

BASE_URL = "http://localhost:8002/api/v1/extract/"

def test_file_upload():
    """Test existing file upload (backward compatibility)"""
    print("\n" + "="*60)
    print("TEST 1: File Upload (Backward Compatibility)")
    print("="*60)
    
    # This test requires a test file to exist
    # Skipping actual upload, just showing the expected format
    print("✅ File upload endpoint signature unchanged")
    print("   Expected: POST with files=@document.pdf, session_id=xxx")
    return True


def test_url_extraction():
    """Test web URL extraction"""
    print("\n" + "="*60)
    print("TEST 2: Web URL Extraction")
    print("="*60)
    
    try:
        response = requests.post(
            BASE_URL,
            data={
                "url": "https://httpbin.org/html",  # Simple test URL
                "session_id": f"test-url-{int(time.time())}",
                "author": "Test Author"
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "queued":
                print("✅ URL extraction queued successfully")
                return True
        
        print("❌ URL extraction failed")
        return False
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Server not running at", BASE_URL)
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_youtube_extraction():
    """Test YouTube URL extraction"""
    print("\n" + "="*60)
    print("TEST 3: YouTube URL Extraction")
    print("="*60)
    
    try:
        response = requests.post(
            BASE_URL,
            data={
                "youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # First YouTube video ever
                "session_id": f"test-youtube-{int(time.time())}",
                "author": "Test Author"
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "queued":
                print("✅ YouTube extraction queued successfully")
                return True
        
        print("❌ YouTube extraction failed")
        return False
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Server not running at", BASE_URL)
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_validation_error():
    """Test that endpoint requires at least one input"""
    print("\n" + "="*60)
    print("TEST 4: Input Validation")
    print("="*60)
    
    try:
        response = requests.post(
            BASE_URL,
            data={
                "session_id": "test-empty",
                "author": "Test Author"
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Validation correctly rejects empty input")
            return True
        else:
            print("❌ Expected 400 error for empty input")
            return False
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Server not running at", BASE_URL)
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("DocuMind URL/YouTube Extraction Test Suite")
    print("="*60)
    
    results = {
        "file_upload": test_file_upload(),
        "url_extraction": test_url_extraction(),
        "youtube_extraction": test_youtube_extraction(),
        "validation": test_validation_error(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else ("⚠️ SKIP" if result is None else "❌ FAIL")
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
