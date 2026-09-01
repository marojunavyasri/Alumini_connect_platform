"""
Tests for Alumni Passout Year Check-in Feature
This module tests the QR code event check-in system with the specific field:
- Alumni users: 'passout_year' field
- Students: 'hall_ticket' field
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mentorship-hub-40.preview.emergentagent.com').rstrip('/')


class TestPassoutYearCheckIn:
    """Test suite for passout_year check-in feature"""
    
    # Class-level storage for test data
    admin_token = None
    alumni_token = None
    student_token = None
    test_event_id = None
    check_in_token = None
    alumni_user_id = None
    student_user_id = None
    alumni_check_in_id = None
    student_check_in_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data that persists across tests"""
        pass
    
    def test_01_admin_login(self):
        """Test admin login to get token for event creation"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@college.com", "password": "Admin@123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        TestPassoutYearCheckIn.admin_token = data["access_token"]
        print(f"Admin token acquired: {data['access_token'][:20]}...")
    
    def test_02_register_test_alumni(self):
        """Register a test alumni user"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        alumni_data = {
            "email": f"TEST_alumni_passout_{timestamp}@example.com",
            "password": "AlumniPass123!",
            "name": f"Test Alumni {timestamp}",
            "batch_year": 2018,
            "department": "Computer Science",
            "current_company": "Test Corp"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=alumni_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "alumni"
        
        TestPassoutYearCheckIn.alumni_token = data["access_token"]
        TestPassoutYearCheckIn.alumni_user_id = data["user"]["id"]
        print(f"Alumni registered with ID: {data['user']['id']}")
    
    def test_03_register_test_student(self):
        """Register a test student user"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        student_data = {
            "email": f"TEST_student_hallticket_{timestamp}@college.edu",
            "password": "StudentPass123!",
            "name": f"Test Student {timestamp}",
            "current_year": 3,
            "department": "Computer Science"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register-student",
            json=student_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "student"
        
        TestPassoutYearCheckIn.student_token = data["access_token"]
        TestPassoutYearCheckIn.student_user_id = data["user"]["id"]
        print(f"Student registered with ID: {data['user']['id']}")
    
    def test_04_create_test_event(self):
        """Admin creates a test event for QR code check-in"""
        assert TestPassoutYearCheckIn.admin_token, "Admin token required"
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        event_data = {
            "title": f"TEST Passout Year Check-in Event {timestamp}",
            "description": "Test event for passout year check-in validation",
            "date": "2026-02-15",
            "location": "Main Auditorium",
            "image_url": ""
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/events",
            json=event_data,
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        
        TestPassoutYearCheckIn.test_event_id = data["event_id"]
        print(f"Event created with ID: {data['event_id']}")
    
    def test_05_get_event_qr_code(self):
        """Get QR code for the event (which contains check-in token)"""
        assert TestPassoutYearCheckIn.admin_token, "Admin token required"
        assert TestPassoutYearCheckIn.test_event_id, "Event ID required"
        
        response = requests.get(
            f"{BASE_URL}/api/events/{TestPassoutYearCheckIn.test_event_id}/qr-code",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "qr_code" in data
        assert "check_in_url" in data
        
        # Extract token from check_in_url
        check_in_url = data["check_in_url"]
        token_start = check_in_url.find("token=") + 6
        TestPassoutYearCheckIn.check_in_token = check_in_url[token_start:]
        print(f"Check-in token extracted: {TestPassoutYearCheckIn.check_in_token[:30]}...")
    
    def test_06_alumni_check_in_with_passout_year(self):
        """Test that alumni can check in with passout_year field"""
        assert TestPassoutYearCheckIn.alumni_token, "Alumni token required"
        assert TestPassoutYearCheckIn.check_in_token, "Check-in token required"
        
        form_data = {
            "token": TestPassoutYearCheckIn.check_in_token,
            "hall_ticket": "2018",  # For alumni, this becomes passout_year
            "name": "Test Alumni User",
            "passout_year": "2018"  # Specific passout_year field for alumni
        }
        
        response = requests.post(
            f"{BASE_URL}/api/events/check-in",
            data=form_data,
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.alumni_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["pending", "approved"]
        print(f"Alumni check-in status: {data['status']}")
    
    def test_07_student_check_in_with_hall_ticket(self):
        """Test that students can check in with hall_ticket field"""
        assert TestPassoutYearCheckIn.student_token, "Student token required"
        assert TestPassoutYearCheckIn.check_in_token, "Check-in token required"
        
        form_data = {
            "token": TestPassoutYearCheckIn.check_in_token,
            "hall_ticket": "CS2024123456",  # Student hall ticket number
            "name": "Test Student User"
            # Note: passout_year is NOT sent for students
        }
        
        response = requests.post(
            f"{BASE_URL}/api/events/check-in",
            data=form_data,
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["pending", "approved"]
        print(f"Student check-in status: {data['status']}")
    
    def test_08_admin_view_pending_check_ins(self):
        """Test admin can view pending check-ins with correct role-specific fields"""
        assert TestPassoutYearCheckIn.admin_token, "Admin token required"
        assert TestPassoutYearCheckIn.test_event_id, "Event ID required"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/events/{TestPassoutYearCheckIn.test_event_id}/pending-check-ins",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        print(f"Found {len(data)} pending check-ins")
        
        # Validate each check-in has proper fields
        for check_in in data:
            assert "id" in check_in
            assert "name" in check_in
            assert "role" in check_in
            assert "hall_ticket" in check_in  # Always present
            
            if check_in["role"] == "alumni":
                # Alumni should have passout_year
                assert "passout_year" in check_in
                print(f"Alumni check-in: {check_in['name']} - Passout Year: {check_in.get('passout_year', check_in.get('hall_ticket'))}")
                TestPassoutYearCheckIn.alumni_check_in_id = check_in["id"]
            else:
                # Student should have hall_ticket only
                print(f"Student check-in: {check_in['name']} - Hall Ticket: {check_in['hall_ticket']}")
                TestPassoutYearCheckIn.student_check_in_id = check_in["id"]
    
    def test_09_approve_alumni_check_in(self):
        """Admin approves alumni check-in"""
        assert TestPassoutYearCheckIn.admin_token, "Admin token required"
        
        if not TestPassoutYearCheckIn.alumni_check_in_id:
            pytest.skip("No alumni check-in to approve")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/events/check-in/{TestPassoutYearCheckIn.alumni_check_in_id}/approve",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Check-in approved"
        print("Alumni check-in approved")
    
    def test_10_approve_student_check_in(self):
        """Admin approves student check-in"""
        assert TestPassoutYearCheckIn.admin_token, "Admin token required"
        
        if not TestPassoutYearCheckIn.student_check_in_id:
            pytest.skip("No student check-in to approve")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/events/check-in/{TestPassoutYearCheckIn.student_check_in_id}/approve",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Check-in approved"
        print("Student check-in approved")
    
    def test_11_alumni_my_passes_shows_passout_year(self):
        """Test alumni /api/alumni/my-passes returns passout_year correctly"""
        assert TestPassoutYearCheckIn.alumni_token, "Alumni token required"
        
        response = requests.get(
            f"{BASE_URL}/api/alumni/my-passes",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.alumni_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            # Find our test event pass
            for pass_data in data:
                if "TEST Passout Year Check-in Event" in pass_data.get("event_title", ""):
                    assert "passout_year" in pass_data
                    assert pass_data["passout_year"] == "2018"
                    print(f"Alumni pass found with passout_year: {pass_data['passout_year']}")
                    break
            else:
                # If we didn't find the specific event, just verify structure
                pass_data = data[0]
                assert "passout_year" in pass_data or "hall_ticket" in pass_data
                print(f"Alumni pass data: passout_year={pass_data.get('passout_year')}")
        else:
            pytest.skip("No passes found for alumni - may need to wait for approval")
    
    def test_12_student_my_passes_shows_hall_ticket(self):
        """Test student /api/students/my-passes returns hall_ticket correctly"""
        assert TestPassoutYearCheckIn.student_token, "Student token required"
        
        response = requests.get(
            f"{BASE_URL}/api/students/my-passes",
            headers={"Authorization": f"Bearer {TestPassoutYearCheckIn.student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            pass_data = data[0]
            assert "hall_ticket" in pass_data
            print(f"Student pass found with hall_ticket: {pass_data['hall_ticket']}")
        else:
            pytest.skip("No passes found for student - may need to wait for approval")


class TestCheckInAPIValidation:
    """Additional API validation tests"""
    
    def test_check_in_requires_token(self):
        """Check-in should require authentication token"""
        form_data = {
            "token": "invalid-token",
            "hall_ticket": "12345",
            "name": "Test User"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/events/check-in",
            data=form_data
            # No Authorization header
        )
        
        # Should fail with 401 Unauthorized
        assert response.status_code == 401
        print("Unauthorized access correctly rejected")
    
    def test_check_in_validates_event_token(self):
        """Check-in should validate the event token"""
        # First, login as admin to get a token
        admin_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@college.com", "password": "Admin@123"}
        )
        admin_token = admin_response.json()["access_token"]
        
        form_data = {
            "token": "invalid-jwt-token",
            "hall_ticket": "12345",
            "name": "Test User"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/events/check-in",
            data=form_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should fail with 400 Bad Request for invalid token
        assert response.status_code == 400
        print("Invalid check-in token correctly rejected")


class TestAdminPendingCheckInsView:
    """Tests for admin pending check-ins dialog showing correct fields"""
    
    def test_pending_check_ins_structure(self):
        """Test that pending check-ins API returns all required fields"""
        # Login as admin
        admin_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@college.com", "password": "Admin@123"}
        )
        admin_token = admin_response.json()["access_token"]
        
        # Get all events
        events_response = requests.get(
            f"{BASE_URL}/api/admin/events",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert events_response.status_code == 200
        events = events_response.json()
        
        if len(events) > 0:
            event_id = events[0]["id"]
            
            # Get pending check-ins for the event
            response = requests.get(
                f"{BASE_URL}/api/admin/events/{event_id}/pending-check-ins",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            
            for check_in in data:
                # Verify required fields exist
                assert "id" in check_in
                assert "event_id" in check_in
                assert "user_id" in check_in
                assert "name" in check_in
                assert "role" in check_in
                assert "status" in check_in
                assert "hall_ticket" in check_in
                
                # For alumni, passout_year should exist
                if check_in["role"] == "alumni":
                    assert "passout_year" in check_in
                    print(f"Alumni pending: passout_year={check_in.get('passout_year')}")
                else:
                    print(f"Student pending: hall_ticket={check_in.get('hall_ticket')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
