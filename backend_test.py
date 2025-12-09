import requests
import sys
import json
from datetime import datetime

class HealthChatbotAPITester:
    def __init__(self, base_url="https://medchatbot-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:300]
                })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'test': name,
                'error': str(e)
            })
            return False, {}

    def test_public_endpoints(self):
        """Test public endpoints"""
        print("\n" + "="*50)
        print("TESTING PUBLIC ENDPOINTS")
        print("="*50)
        
        # Test chat endpoint with different languages
        languages = ['en', 'hi', 'kn']
        for lang in languages:
            success, response = self.run_test(
                f"Chat in {lang}",
                "POST",
                "chat",
                200,
                data={"query": "What is fever?", "language": lang}
            )
            if success and 'response' in response:
                print(f"   AI Response: {response['response'][:100]}...")
        
        # Test inventory query
        success, response = self.run_test(
            "Chat - Inventory Query",
            "POST", 
            "chat",
            200,
            data={"query": "What medicines are available?", "language": "en"}
        )
        
        # Test get alerts
        success, response = self.run_test(
            "Get Alerts",
            "GET",
            "get-alerts", 
            200
        )

    def test_worker_login(self):
        """Test worker authentication"""
        print("\n" + "="*50)
        print("TESTING WORKER AUTHENTICATION")
        print("="*50)
        
        # Test successful login
        success, response = self.run_test(
            "Worker Login - Valid Credentials",
            "POST",
            "worker/login",
            200,
            data={"username": "healthworker", "password": "securepass"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token obtained: {self.token[:50]}...")
        
        # Test invalid login
        success, response = self.run_test(
            "Worker Login - Invalid Credentials", 
            "POST",
            "worker/login",
            401,
            data={"username": "wronguser", "password": "wrongpass"}
        )

    def test_worker_endpoints(self):
        """Test protected worker endpoints"""
        if not self.token:
            print("\n❌ No token available, skipping worker endpoint tests")
            return
            
        print("\n" + "="*50)
        print("TESTING WORKER ENDPOINTS")
        print("="*50)
        
        # Test get inventory
        success, response = self.run_test(
            "Get Inventory",
            "GET",
            "worker/get-inventory",
            200
        )
        
        # Test broadcast alert
        success, response = self.run_test(
            "Broadcast Alert",
            "POST",
            "worker/broadcast-alert",
            200,
            data={"message": f"Test alert from API test - {datetime.now().strftime('%H:%M:%S')}"}
        )
        
        # Test update inventory
        success, response = self.run_test(
            "Update Inventory",
            "POST", 
            "worker/update-inventory",
            200,
            data={"item_name": "Test Medicine", "quantity": 100}
        )
        
        # Test unauthorized access (without token)
        temp_token = self.token
        self.token = None
        success, response = self.run_test(
            "Unauthorized Access Test",
            "GET",
            "worker/get-inventory", 
            401
        )
        self.token = temp_token

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        if self.failed_tests:
            print(f"\n❌ Failed tests ({len(self.failed_tests)}):")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"   {i}. {test['test']}")
                if 'error' in test:
                    print(f"      Error: {test['error']}")
                else:
                    print(f"      Expected: {test['expected']}, Got: {test['actual']}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80

def main():
    print("🏥 Health Chatbot API Testing")
    print("=" * 60)
    
    tester = HealthChatbotAPITester()
    
    # Run all tests
    tester.test_public_endpoints()
    tester.test_worker_login()
    tester.test_worker_endpoints()
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())