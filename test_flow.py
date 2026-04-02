import os
os.environ["PYTHONPATH"] = "z:\\s2c"

from app import app
from database.db import get_db_connection
import io

def test_full_flow():
    with app.test_client() as client:
        # Register
        print("Registering test user...")
        res = client.post('/register', data={
            'username': 'testflowuser',
            'email': 'testflowuser@example.com',
            'password': 'testflowpassword123'
        }, follow_redirects=True)
        print("Register status:", res.status_code)
        
        # Login
        print("Logging in...")
        res = client.post('/login', data={
            'email': 'testflowuser@example.com',
            'password': 'testflowpassword123'
        }, follow_redirects=True)
        print("Login status:", res.status_code)
        assert b'Logout' in res.data, "Login failed!"
        
        # Dashboard
        print("Accessing dashboard...")
        res = client.get('/dashboard')
        print("Dashboard status:", res.status_code)
        
        # Upload
        print("Uploading test_sketch.png...")
        test_file_path = os.path.join(os.path.dirname(__file__), 'test_sketch.png')
        if not os.path.exists(test_file_path):
            # Create a dummy image
            from PIL import Image
            img = Image.new('RGB', (100, 100), color = 'red')
            img.save(test_file_path)
            
        with open(test_file_path, 'rb') as f:
            data = {
                'title': 'Test Flow Project',
                'sketch': (io.BytesIO(f.read()), 'test_sketch.png')
            }
        
        res = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        print("Upload and Detect status:", res.status_code)
        html_code = res.data.decode('utf-8')
        
        if 'Java Code' in html_code:
            print("[PASS] 'Java Code' tab found in preview page.")
        else:
            print("[FAIL] 'Java Code' tab MISSING.")
            
        if 'import javax.swing' in html_code:
            print("[PASS] Generated Java code content found on preview page.")
        else:
            print("[FAIL] Java code content MISSING.")

        if 'class="nav-link"' in html_code and 'Java' in html_code:
            print("[PASS] Nav links for tabs detected.")
            
        print("Flow complete.")

if __name__ == '__main__':
    # Need app context for db
    with app.app_context():
        test_full_flow()
