import urllib.request
import json
import sys
import ssl
import subprocess

API_KEY = "AIzaSyAgvP7u0IrJwKZTE7WGnDmwTGmRg5W2BI4"
PROJECT_ID = "vcatch-chat"
EMAIL = "vc0646@vcatch.internal"
PASSWORD = "Admin@2026"
EMP_ID = "VC0646"

def make_request_urllib(url, data=None, headers=None, method="POST"):
    if headers is None:
        headers = {}
    headers["Content-Type"] = "application/json"
    
    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    
    # Create unverified SSL context
    ctx = ssl._create_unverified_context()
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data), None
    except urllib.error.HTTPError as e:
        err_data = e.read().decode("utf-8")
        try:
            return None, json.loads(err_data)
        except Exception:
            return None, {"error": {"message": err_data}}
    except Exception as e:
        return None, {"error": {"message": str(e)}}

def make_request_curl(url, data=None, headers=None, method="POST"):
    # Fallback using native curl command
    cmd = ["curl", "-s", "-X", method, url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.extend(["-H", "Content-Type: application/json"])
    
    if data is not None:
        cmd.extend(["-d", json.dumps(data)])
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout), None
    except subprocess.CalledProcessError as e:
        return None, {"error": {"message": f"curl failed: {e.stderr}"}}
    except Exception as e:
        return None, {"error": {"message": str(e)}}

def make_request(url, data=None, headers=None, method="POST"):
    # Try urllib first, fallback to curl
    res, err = make_request_urllib(url, data, headers, method)
    if err and "Remote end closed connection" in str(err):
        print("urllib failed with connection closure. Falling back to curl...")
        return make_request_curl(url, data, headers, method)
    return res, err

def main():
    print("--- Creating/Verifying Master Admin User ---")
    
    # 1. Try to sign up
    signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "returnSecureToken": True
    }
    
    print(f"Registering user {EMAIL} on Firebase Auth...")
    res, err = make_request(signup_url, payload)
    
    id_token = None
    uid = None
    
    if err:
        err_msg = ""
        if isinstance(err, dict):
            err_msg = err.get("error", {}).get("message", "")
        else:
            err_msg = str(err)
            
        if "EMAIL_EXISTS" in err_msg:
            print("User already exists in Firebase Auth. Attempting to sign in...")
            signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
            res, err = make_request(signin_url, payload)
            if err:
                print("Sign in failed:", err)
                sys.exit(1)
            else:
                id_token = res["idToken"]
                uid = res["localId"]
                print("Sign in successful.")
        else:
            print("Sign up failed:", err)
            sys.exit(1)
    else:
        id_token = res["idToken"]
        uid = res["localId"]
        print("Registration successful.")
        
    print(f"User UID: {uid}")
    
    # 2. Write/Overwrite document in Firestore
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users/{uid}"
    
    user_doc = {
        "fields": {
            "empId": {"stringValue": EMP_ID},
            "firstName": {"stringValue": "Master"},
            "lastName": {"stringValue": "Admin"},
            "phone": {"stringValue": "+91 9876541006"},
            "dept": {"stringValue": "Operations"},
            "pass": {"stringValue": PASSWORD},
            "initials": {"stringValue": "MA"},
            "color": {"stringValue": "#E8A020"},
            "status": {"stringValue": "online"},
            "role": {"stringValue": "Admin"},
            "active": {"booleanValue": True}
        }
    }
    
    headers = {
        "Authorization": f"Bearer {id_token}"
    }
    
    print("Writing user details to Firestore...")
    res, err = make_request(firestore_url, user_doc, headers=headers, method="PATCH")
    
    if err:
        print("Firestore write failed!")
        print("Error details:", json.dumps(err, indent=2))
        print("\nPossible solutions:")
        print("1. If permission denied, update Firestore rules in Firebase Console to allow write access for authenticated users.")
        print("   Example rule:")
        print("   match /users/{userId} {")
        print("     allow read, write: if request.auth != null && request.auth.uid == userId;")
        print("   }")
    else:
        print("Firestore write successful!")
        print("Master Admin is now fully created and configured.")
        print(f"Username / Employee ID: {EMP_ID}")
        print(f"Password: {PASSWORD}")

if __name__ == "__main__":
    main()
