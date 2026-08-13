import json
import time
import sys
import datetime
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, payload=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            try:
                resp_json = json.loads(body)
            except Exception:
                resp_json = body
            return status, resp_json
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            resp_json = json.loads(body)
        except Exception:
            resp_json = body
        return e.code, resp_json
    except Exception as e:
        print(f"Error requesting {url}: {e}")
        raise

def run_verification():
    print("=" * 60)
    print("MIMO CORE FLOWS VERIFICATION")
    print(f"Target Server: {BASE_URL}")
    print("=" * 60)
    print()

    # Generate unique test user email
    timestamp = int(time.time())
    email = f"test_user_{timestamp}@example.com"
    password = "TestPassword123!"
    display_name = f"Test User {timestamp}"

    # 1. POST /auth/register
    print("Step 1: Register User -> POST /auth/register")
    reg_payload = {
        "email": email,
        "password": password,
        "role": "student",
        "display_name": display_name
    }
    status, res = make_request("POST", "/auth/register", payload=reg_payload)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 201, f"Expected 201 Created for register, got {status}"
    assert "access_token" in res, "No access_token returned in registration response"
    token = res["access_token"]
    print("✓ POST /auth/register PASSED (201 Created)\n")

    # 2. POST /auth/login
    print("Step 2: Login User -> POST /auth/login")
    login_payload = {
        "email": email,
        "password": password
    }
    status, res = make_request("POST", "/auth/login", payload=login_payload)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for login, got {status}"
    assert "access_token" in res, "No access_token returned in login response"
    login_token = res["access_token"]
    print("✓ POST /auth/login PASSED (200 OK)\n")

    headers = {"Authorization": f"Bearer {login_token}"}

    # 3. GET /auth/me
    print("Step 3: Get Current User Profile -> GET /auth/me")
    status, res = make_request("GET", "/auth/me", headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for /auth/me, got {status}"
    assert res.get("email") == email, "User email mismatch in /auth/me response"
    print("✓ GET /auth/me PASSED (200 OK)\n")

    # 4. POST /onboarding/complete
    print("Step 4: Complete Onboarding -> POST /onboarding/complete")
    onboard_payload = {
        "course": "Computer Science 101",
        "age": 20,
        "education_level": "Undergraduate",
        "ai_engine": "gemini",
        "api_key": "test_key_12345",
        "wake_time": "08:00",
        "sleep_time": "23:00",
        "study_goal_minutes": 120
    }
    status, res = make_request("POST", "/onboarding/complete", payload=onboard_payload, headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for /onboarding/complete, got {status}"
    assert res.get("status") == "success", "Onboarding response status not success"
    print("✓ POST /onboarding/complete PASSED (200 OK)\n")

    # 5. POST /assignments/
    due_in_3_days = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    print(f"Step 5: Create Assignment -> POST /assignments/ (due: {due_in_3_days})")
    assign_payload = {
        "title": "Algorithms Homework 1",
        "subject": "Computer Science",
        "due_date": due_in_3_days,
        "priority": "high",
        "notes": "Chapter 1 and 2 problems"
    }
    status, res = make_request("POST", "/assignments/", payload=assign_payload, headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 201, f"Expected 201 Created for assignment creation, got {status}"
    assert "id" in res, "No assignment ID in response"
    assignment_id = res["id"]
    print(f"✓ POST /assignments/ PASSED (201 Created, ID: {assignment_id})\n")

    # 6. GET /assignments/
    print("Step 6: List All Assignments -> GET /assignments/")
    status, res = make_request("GET", "/assignments/", headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for GET /assignments/, got {status}"
    assert isinstance(res, list) and len(res) > 0, "Assignments list is empty"
    print("✓ GET /assignments/ PASSED (200 OK)\n")

    # 7. GET /assignments/upcoming
    print("Step 7: List Upcoming Assignments -> GET /assignments/upcoming")
    status, res = make_request("GET", "/assignments/upcoming", headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for GET /assignments/upcoming, got {status}"
    assert isinstance(res, list) and len(res) > 0, "Upcoming assignments list is empty"
    print("✓ GET /assignments/upcoming PASSED (200 OK)\n")

    # 8. POST /assignments/{id}/done
    print(f"Step 8: Mark Assignment Done -> POST /assignments/{assignment_id}/done")
    status, res = make_request("POST", f"/assignments/{assignment_id}/done", headers=headers)
    print(f"Status Code: {status}")
    print(f"Response: {json.dumps(res, indent=2)}")
    assert status == 200, f"Expected 200 OK for POST /assignments/{assignment_id}/done, got {status}"
    assert res.get("ok") is True, "Response ok field is not True"
    print(f"✓ POST /assignments/{assignment_id}/done PASSED (200 OK)\n")

    print("=" * 60)
    print("ALL CORE FLOW VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as err:
        print(f"\n❌ VERIFICATION FAILED: {err}")
        sys.exit(1)
