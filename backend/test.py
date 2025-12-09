# backend/test.py
import requests
import json

# Server URL
BASE_URL = "http://localhost:5000"

def print_step(step_num, description):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*60}")

def test_home():
    """Test 1: Check if server is running"""
    print_step(1, "Testing if server is running")
    
    try:
        response = requests.get(BASE_URL)
        print(f"✅ Server responded with status: {response.status_code}")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        return True
    except:
        print("❌ Server is NOT running!")
        print("💡 Run: python server.py in another terminal")
        return False

def test_health():
    """Test 2: Health check"""
    print_step(2, "Testing health endpoint")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.status_code}")
    print(f"📄 Response: {response.json()}")

def test_get_test():
    """Test 3: Test endpoint (GET)"""
    print_step(3, "Testing GET /test endpoint")
    
    response = requests.get(f"{BASE_URL}/test")
    print(f"✅ Test endpoint: {response.status_code}")
    print(f"📄 Response: {json.dumps(response.json(), indent=2)}")

def test_upload_without_data():
    """Test 4: Upload without data (should fail nicely)"""
    print_step(4, "Testing upload WITHOUT data (should fail)")
    
    response = requests.post(f"{BASE_URL}/upload")
    print(f"📄 Status code: {response.status_code}")
    print(f"📄 Response: {json.dumps(response.json(), indent=2)}")

def test_upload_with_demo_data():
    """Test 5: Upload with demo data (should succeed)"""
    print_step(5, "Testing upload WITH demo data")
    
    # Create demo data
    demo_data = {
        "image_name": "trash_pile_001.jpg",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timestamp": "2024-01-15T10:30:00",
        "device_id": "android_phone_123"
    }
    
    print(f"📤 Sending demo data: {json.dumps(demo_data, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/upload",
        json=demo_data,  # Send as JSON
        headers={"Content-Type": "application/json"}
    )
    
    print(f"✅ Status code: {response.status_code}")
    print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n🎉 SUCCESS! Backend is working correctly!")
        print("✨ You can now connect your Android app to this backend.")

def run_all_tests():
    """Run all tests in order"""
    print("\n" + "🌟" * 30)
    print("   AUDITOS BACKEND - QUICK TEST")
    print("🌟" * 30)
    
    # Test 1: Check server
    if not test_home():
        return  # Stop if server isn't running
    
    # Run remaining tests
    test_health()
    test_get_test()
    test_upload_without_data()
    test_upload_with_demo_data()
    
    print("\n" + "✅" * 30)
    print("   ALL TESTS COMPLETED!")
    print("✅" * 30)
    print("\n📱 Next: Give this URL to Android team:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Upload endpoint: {BASE_URL}/upload")

if __name__ == "__main__":
    run_all_tests()