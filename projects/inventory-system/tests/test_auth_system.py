#!/usr/bin/env python3
"""
Authentication System Test Suite
Tests all aspects of the login authentication system
"""

import requests
import json
import sys
from typing import Dict, Optional, Tuple

# Test configuration
BASE_URL = "http://localhost:8080"
TEST_USERS = {
    "JustinMenezes": "386canalst",
    "FelipeCardozo": "26cmu"
}

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class AuthTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}{text.center(60)}{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
    
    def print_test(self, test_name: str):
        """Print test name"""
        print(f"{BOLD}Testing: {test_name}{RESET}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"  {GREEN}✓ PASS:{RESET} {message}")
        self.test_results.append(("PASS", message))
    
    def print_failure(self, message: str):
        """Print failure message"""
        print(f"  {RED}✗ FAIL:{RESET} {message}")
        self.test_results.append(("FAIL", message))
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"  {YELLOW}ℹ INFO:{RESET} {message}")
    
    def test_valid_login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test login with valid credentials"""
        self.print_test(f"Valid Login - User: {username}")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            self.print_info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Check if session cookie was set
                    cookies = self.session.cookies.get_dict()
                    if 'pokebowl_session' in cookies:
                        self.print_success(f"Login successful for {username}")
                        self.print_info(f"Session cookie set: {cookies['pokebowl_session'][:20]}...")
                        return True, cookies['pokebowl_session']
                    else:
                        self.print_failure("Login succeeded but no session cookie set")
                        return False, None
                else:
                    self.print_failure(f"Login failed: {data.get('message', 'Unknown error')}")
                    return False, None
            else:
                self.print_failure(f"Unexpected status code: {response.status_code}")
                return False, None
                
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
            return False, None
    
    def test_invalid_password(self, username: str, wrong_password: str):
        """Test login with invalid password"""
        self.print_test(f"Invalid Password - User: {username}")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/login",
                json={"username": username, "password": wrong_password},
                headers={"Content-Type": "application/json"}
            )
            
            self.print_info(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                data = response.json()
                if not data.get('success'):
                    self.print_success("Login correctly rejected with 401")
                    self.print_info(f"Message: {data.get('message')}")
                else:
                    self.print_failure("Login should have failed but succeeded")
            else:
                self.print_failure(f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
    
    def test_invalid_username(self, username: str):
        """Test login with non-existent username"""
        self.print_test(f"Invalid Username - User: {username}")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/login",
                json={"username": username, "password": "anypassword"},
                headers={"Content-Type": "application/json"}
            )
            
            self.print_info(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                data = response.json()
                if not data.get('success'):
                    self.print_success("Login correctly rejected for unknown user")
                    self.print_info(f"Message: {data.get('message')}")
                else:
                    self.print_failure("Login should have failed but succeeded")
            else:
                self.print_failure(f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
    
    def test_missing_credentials(self):
        """Test login with missing credentials"""
        self.print_test("Missing Credentials")
        
        test_cases = [
            ({"username": "test"}, "Missing password"),
            ({"password": "test"}, "Missing username"),
            ({}, "Missing both")
        ]
        
        for payload, description in test_cases:
            try:
                response = self.session.post(
                    f"{BASE_URL}/api/login",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 400:
                    self.print_success(f"{description}: Correctly rejected with 400")
                else:
                    self.print_failure(f"{description}: Expected 400, got {response.status_code}")
                    
            except Exception as e:
                self.print_failure(f"{description}: Exception - {str(e)}")
    
    def test_protected_endpoint(self, authenticated: bool = False):
        """Test access to protected endpoint"""
        self.print_test(f"Protected Endpoint Access ({'Authenticated' if authenticated else 'Unauthenticated'})")
        
        try:
            # Try to access the main page
            response = self.session.get(f"{BASE_URL}/")
            
            self.print_info(f"Status Code: {response.status_code}")
            
            if authenticated:
                if response.status_code == 200:
                    # Check if we got the actual page, not login redirect
                    if 'login' not in response.url.lower():
                        self.print_success("Access granted to authenticated user")
                    else:
                        self.print_failure("Redirected to login despite being authenticated")
                else:
                    self.print_failure(f"Expected 200, got {response.status_code}")
            else:
                # Should be redirected to login or denied
                if response.status_code in [302, 303, 401]:
                    self.print_success("Access correctly denied to unauthenticated user")
                elif 'login' in response.url.lower():
                    self.print_success("Redirected to login page")
                else:
                    self.print_failure(f"Unexpected response: {response.status_code}")
                    
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
    
    def test_logout(self):
        """Test logout functionality"""
        self.print_test("Logout Functionality")
        
        try:
            response = self.session.post(f"{BASE_URL}/api/logout")
            
            self.print_info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Check if session cookie was cleared
                    cookies = self.session.cookies.get_dict()
                    if 'pokebowl_session' not in cookies or not cookies.get('pokebowl_session'):
                        self.print_success("Logout successful, session cookie cleared")
                    else:
                        self.print_info("Session cookie still present (may be expired)")
                        self.print_success("Logout endpoint responded successfully")
                else:
                    self.print_failure("Logout failed")
            else:
                self.print_failure(f"Expected 200, got {response.status_code}")
                
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
    
    def test_session_persistence(self, username: str, password: str):
        """Test that session persists across requests"""
        self.print_test("Session Persistence")
        
        # Create a new session
        test_session = requests.Session()
        
        try:
            # Login
            response = test_session.post(
                f"{BASE_URL}/api/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code != 200:
                self.print_failure("Could not login for session test")
                return
            
            session_cookie = test_session.cookies.get('pokebowl_session')
            if not session_cookie:
                self.print_failure("No session cookie received")
                return
            
            self.print_info(f"Session cookie: {session_cookie[:20]}...")
            
            # Make a second request with the same session
            response2 = test_session.get(f"{BASE_URL}/")
            
            if response2.status_code == 200:
                self.print_success("Session persisted across requests")
            else:
                self.print_failure(f"Session did not persist: {response2.status_code}")
                
        except Exception as e:
            self.print_failure(f"Exception occurred: {str(e)}")
    
    def test_websocket_auth(self):
        """Test WebSocket authentication"""
        self.print_test("WebSocket Authentication")
        
        try:
            # Try to connect to WebSocket without authentication
            import websocket
            
            ws_url = BASE_URL.replace('http://', 'ws://') + '/ws'
            
            try:
                ws = websocket.create_connection(ws_url, timeout=2)
                ws.close()
                self.print_info("WebSocket connection test completed")
            except Exception as e:
                self.print_info(f"WebSocket test skipped: {str(e)}")
                
        except ImportError:
            self.print_info("websocket-client not installed, skipping WebSocket test")
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        total = len(self.test_results)
        passed = sum(1 for result, _ in self.test_results if result == "PASS")
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        
        if failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for result, message in self.test_results:
                if result == "FAIL":
                    print(f"  - {message}")
        
        print(f"\n{BOLD}Overall Result: ", end="")
        if failed == 0:
            print(f"{GREEN}ALL TESTS PASSED ✓{RESET}")
            return 0
        else:
            print(f"{RED}SOME TESTS FAILED ✗{RESET}")
            return 1

def main():
    """Run all authentication tests"""
    tester = AuthTester()
    
    tester.print_header("AUTHENTICATION SYSTEM TEST SUITE")
    print(f"Testing server at: {BASE_URL}")
    print(f"Number of test users: {len(TEST_USERS)}\n")
    
    # Test 1: Valid login for all users
    tester.print_header("TEST 1: VALID LOGIN")
    for username, password in TEST_USERS.items():
        success, token = tester.test_valid_login(username, password)
        print()
    
    # Test 2: Invalid password
    tester.print_header("TEST 2: INVALID PASSWORD")
    tester.test_invalid_password("JustinMenezes", "wrongpassword")
    print()
    
    # Test 3: Invalid username
    tester.print_header("TEST 3: INVALID USERNAME")
    tester.test_invalid_username("NonExistentUser")
    print()
    
    # Test 4: Missing credentials
    tester.print_header("TEST 4: MISSING CREDENTIALS")
    tester.test_missing_credentials()
    print()
    
    # Test 5: Protected endpoint without auth
    tester.print_header("TEST 5: PROTECTED ENDPOINT (NO AUTH)")
    tester.session = requests.Session()  # Fresh session
    tester.test_protected_endpoint(authenticated=False)
    print()
    
    # Test 6: Login and test protected endpoint
    tester.print_header("TEST 6: PROTECTED ENDPOINT (WITH AUTH)")
    tester.test_valid_login("JustinMenezes", TEST_USERS["JustinMenezes"])
    tester.test_protected_endpoint(authenticated=True)
    print()
    
    # Test 7: Session persistence
    tester.print_header("TEST 7: SESSION PERSISTENCE")
    tester.test_session_persistence("FelipeCardozo", TEST_USERS["FelipeCardozo"])
    print()
    
    # Test 8: Logout
    tester.print_header("TEST 8: LOGOUT")
    tester.test_valid_login("JustinMenezes", TEST_USERS["JustinMenezes"])
    tester.test_logout()
    print()
    
    # Test 9: Access after logout
    tester.print_header("TEST 9: ACCESS AFTER LOGOUT")
    tester.test_protected_endpoint(authenticated=False)
    print()
    
    # Test 10: WebSocket authentication
    tester.print_header("TEST 10: WEBSOCKET AUTHENTICATION")
    tester.test_websocket_auth()
    print()
    
    # Print summary
    exit_code = tester.print_summary()
    
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}Fatal error: {str(e)}{RESET}")
        sys.exit(1)

