import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils import config

def main():
    """
    Interactive OAuth setup wizard.
    
    Steps:
    1. Check if credentials.json exists
    2. Run OAuth flow (opens browser)
    3. User authorizes in browser
    4. Save token to gmail_token.json
    5. Test API connection
    """
    print("=" * 70)
    print("GOOGLE GMAIL OAUTH SETUP")
    print("=" * 70)
    
    credentials_path = config.GOOGLE_TOKENS_DIR / "credentials.json"
    token_path = config.GOOGLE_TOKENS_DIR / "gmail_token.json"
    
    # Step 1: Check credentials file
    print("\n📋 Step 1: Checking credentials file...")
    print("-" * 70)
    
    if not credentials_path.exists():
        print("❌ credentials.json not found!")
        print(f"\n   Expected location: {credentials_path}")
        print("\n   To get credentials.json:")
        print("   1. Go to: https://console.cloud.google.com/")
        print("   2. Create project (or select existing)")
        print("   3. Enable Gmail API")
        print("   4. Configure OAuth consent screen")
        print("   5. Create OAuth Desktop credentials")
        print("   6. Download JSON file")
        print(f"   7. Move to: {credentials_path}")
        print("\n   See detailed guide above or in README.md")
        sys.exit(1)
    
    print(f"✅ Found credentials.json at: {credentials_path}")
    
    # Step 2: Import Google libraries
    print("\n📋 Step 2: Loading Google API libraries...")
    print("-" * 70)
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        print("✅ Google API libraries loaded")
    
    except ImportError as e:
        print(f"❌ Google API library not installed: {e}")
        print("\n   Install with:")
        print("   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)
    
    # Step 3: Define scopes
    print("\n📋 Step 3: Configuring API permissions...")
    print("-" * 70)
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
    
    print("✅ Requesting Gmail permission:")
    print("   - gmail.compose: Create email drafts")
    print("   (Does NOT allow reading emails or sending)")
    
    # Step 4: Check existing token
    print("\n📋 Step 4: Checking for existing token...")
    print("-" * 70)
    
    creds = None
    
    if token_path.exists():
        print(f"   Found existing token at: {token_path}")
        
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            
            if creds and creds.valid:
                print("✅ Existing token is valid!")
                print("\n   You're already authorized. No need to re-authorize.")
                
                # Test connection
                test_connection(creds)
                return
            
            elif creds and creds.expired and creds.refresh_token:
                print("   Token expired, refreshing...")
                creds.refresh(Request())
                
                # Save refreshed token
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                
                print("✅ Token refreshed successfully!")
                
                # Test connection
                test_connection(creds)
                return
            
            else:
                print("   Token invalid, need new authorization")
        
        except Exception as e:
            print(f"   Error loading token: {e}")
            print("   Will get new authorization")
    
    else:
        print("   No existing token found")
    
    # Step 5: Run OAuth flow
    print("\n📋 Step 5: Starting OAuth authorization...")
    print("-" * 70)
    print("\n⚠️  IMPORTANT:")
    print("   - A browser window will open")
    print("   - Log in with your Google account")
    print("   - Click 'Allow' to grant permissions")
    print("   - You may see 'App not verified' warning - click 'Advanced' → 'Go to Voice Assistant (unsafe)'")
    print("     (This is normal for development apps)")
    
    input("\n   Press Enter to open browser and start authorization...")
    
    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            SCOPES
        )
        
        # This opens browser and starts local server
        creds = flow.run_local_server(port=0)
        
        print("\n✅ Authorization successful!")
        
        # Step 6: Save token
        print("\n📋 Step 6: Saving token...")
        print("-" * 70)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ Token saved to: {token_path}")
        
        # Step 7: Test connection
        print("\n📋 Step 7: Testing Gmail API connection...")
        print("-" * 70)
        
        test_connection(creds)
        
        print("\n" + "=" * 70)
        print("✅ SETUP COMPLETE!")
        print("=" * 70)
        print("\n   You can now use Gmail drafts in your voice assistant.")
        print("   Try saying: 'Draft an email to john@example.com'")
    
    except Exception as e:
        print(f"\n❌ Authorization failed: {e}")
        print("\n   Common issues:")
        print("   1. Wrong Google account (must be added in OAuth consent screen)")
        print("   2. Didn't click 'Allow' in browser")
        print("   3. Firewall blocking localhost:8080")
        print("\n   Try running this script again")
        sys.exit(1)


def test_connection(creds):
    """
    Test Gmail API connection.
    
    Args:
        creds: Google OAuth credentials
    """
    try:
        from googleapiclient.discovery import build
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        # Test: Get user profile
        profile = service.users().getProfile(userId='me').execute()
        
        email = profile.get('emailAddress', 'Unknown')
        
        print(f"✅ Successfully connected to Gmail API")
        print(f"   Authorized account: {email}")
    
    except Exception as e:
        print(f"⚠️  Warning: Could not test connection: {e}")
        print("   Token saved, but test failed. Try using the tool to verify.")


if __name__ == "__main__":
    main()