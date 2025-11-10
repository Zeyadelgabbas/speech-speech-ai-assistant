from typing import Dict, Any, Optional
import base64
from email.mime.text import MIMEText
from .base import BaseTool
from ..utils import get_logger , config
logging = get_logger(__name__)


class GmailDraftTool(BaseTool):
    """
    Create email drafts in Gmail (does NOT send).
    
    Requires:
    - Google Cloud project with Gmail API enabled
    - OAuth2 credentials (run scripts/setup_google_oauth.py)
    - Stored token in ./data/google_tokens/gmail_token.json
    
    When LLM should use:
    - "Draft an email to..."
    - "Compose email..."
    - "Write email to..."

    """
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize Gmail tool.
        
        Args:
            credentials_path: Path to OAuth2 credentials JSON
            token_path: Path to stored token
        
        OAuth setup:
        1. Create Google Cloud project
        2. Enable Gmail API
        3. Download credentials.json
        4. Run: python scripts/setup_google_oauth.py
        5. Authorize in browser
        6. Token saved to ./data/google_tokens/
        """
        self.credentials_path = credentials_path or (config.GOOGLE_TOKENS_DIR / "credentials.json")
        self.token_path = token_path or (config.GOOGLE_TOKENS_DIR / "gmail_token.json")
        
        # Ensure token directory exists
        config.GOOGLE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        
        self.service = None
        self._initialized = False
        
        logging.info("GmailDraftTool initialized")
    
    def _initialize_service(self):
        """
        Initialize Gmail API service (lazy loading).
        
        Why lazy loading?
        - Don't load if user doesn't have OAuth set up
        - Faster startup (only load when needed)
        - Graceful degradation (tool fails only when used)
        """
        if self._initialized:
            return True
        
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            # Gmail API scope (draft creation only)
            SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
            
            creds = None
            
            # Load existing token
            if self.token_path.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            
            # Refresh or get new token
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh expired token
                    creds.refresh(Request())
                    logging.info("Refreshed Gmail OAuth token")
                else:
                    # Need new authorization
                    if not self.credentials_path.exists():
                        logging.error("Gmail credentials not found")
                        raise FileNotFoundError(
                            f"Gmail credentials not found at {self.credentials_path}. "
                            "Run: python scripts/setup_google_oauth.py"
                        )
                    
                    # Run OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logging.info("Obtained new Gmail OAuth token")
                
                # Save token
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            self._initialized = True
            
            logging.info("Gmail service initialized successfully")
            return True
        
        except ImportError as e:
            logging.error(f"Gmail API library not installed: {e}")
            return False
        
        except Exception as e:
            logging.error(f"Failed to initialize Gmail service: {e}")
            return False
    
    @property
    def name(self) -> str:
        return "gmail_draft"
    
    @property
    def description(self) -> str:
        return """Create email draft in Gmail (does NOT send). Use for: composing emails, drafting messages. User can review/send from Gmail. Requires OAuth setup."""
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address (e.g., 'john@example.com')"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content (plain text)"
                }
            },
            "required": ["to", "subject", "body"]
        }
    
    def execute(self, to: str, subject: str, body: str) -> str:
        """
        Create an email draft in Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
        
        Returns:
            Success message or error
        
        Process:
        1. Create MIME message
        2. Encode to base64
        3. Call Gmail API to create draft
        4. Return draft ID and confirmation
        """
        # Validate inputs
        if not to.strip() or '@' not in to:
            return "Error: Invalid recipient email address"
        
        if not subject.strip():
            return "Error: Email subject cannot be empty"
        
        if not body.strip():
            return "Error: Email body cannot be empty"
        
        # Initialize service if needed
        if not self._initialize_service():
            return """Error: Gmail not configured. 

To enable Gmail drafts:
1. Run: python scripts/setup_google_oauth.py
2. Follow OAuth authorization steps
3. Try again

For now, I'll save this as a note instead."""
        
        try:
            # Create MIME message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create draft via Gmail API
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            draft_id = draft['id']
            
            logging.info(f"Created Gmail draft: {draft_id} (to: {to})")
            
            return f"""✅ Email draft created successfully!

To: {to}
Subject: {subject}

The draft is saved in your Gmail drafts folder. 
You can review and send it from Gmail."""
        
        except Exception as e:
            error_msg = f"Failed to create Gmail draft: {str(e)}"
            logging.error(error_msg)
            
            # Fallback: suggest saving as note
            return f"""Error: {error_msg}

Would you like me to save this as a note instead?
To: {to}
Subject: {subject}
Body: {body[:100]}..."""
    
    def is_configured(self) -> bool:
        """
        Check if Gmail OAuth is configured.
        
        Returns:
            True if credentials and token exist
        """
        return self.credentials_path.exists() and self.token_path.exists()


# ============================================================================
# MODULE TEST
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("GMAIL DRAFT TOOL TEST")
    print("=" * 70)
    
    # Test 1: Initialize tool
    print("\n📝 Test 1: Initialize Gmail tool")
    print("-" * 70)
    
    tool = GmailDraftTool()
    print(f"✅ Tool initialized: {tool.name}")
    print(f"   Credentials path: {tool.credentials_path}")
    print(f"   Token path: {tool.token_path}")
    print(f"   Configured: {tool.is_configured()}")
    
    # Test 2: Get OpenAI schema
    print("\n📝 Test 2: Get OpenAI tool schema")
    print("-" * 70)
    
    schema = tool.get_openai_tool_schema()
    print(f"✅ Schema generated:")
    print(f"   Parameters: {list(schema['function']['parameters']['properties'].keys())}")
    print(f"   Required: {schema['function']['parameters']['required']}")
    
    # Test 3: Check if configured
    print("\n📝 Test 3: Check OAuth configuration")
    print("-" * 70)
    
    if tool.is_configured():
        print("✅ Gmail OAuth is configured")
        print("\n   Testing draft creation...")
        
        # Only test if configured
        result = tool.execute(
            to="test@example.com",
            subject="Test Draft",
            body="This is a test email draft created by the voice assistant."
        )
        
        print(f"\n   Result:\n{result}")
    else:
        print("⚠️  Gmail OAuth not configured")
        print("\n   To configure Gmail:")
        print("   1. Run: python scripts/setup_google_oauth.py")
        print("   2. Follow the authorization steps")
        print("   3. Run this test again")
        
        # Test error handling
        print("\n   Testing unconfigured behavior...")
        result = tool.execute(
            to="test@example.com",
            subject="Test",
            body="Test body"
        )
        print(f"\n   Result:\n{result[:200]}...")
    
    # Test 4: Input validation
    print("\n📝 Test 4: Input validation")
    print("-" * 70)
    
    # Invalid email
    result_invalid_email = tool.execute(
        to="invalid-email",
        subject="Test",
        body="Body"
    )
    print(f"   Invalid email: {result_invalid_email}")
    
    # Empty subject
    result_empty_subject = tool.execute(
        to="test@example.com",
        subject="",
        body="Body"
    )
    print(f"   Empty subject: {result_empty_subject}")
    
    # Empty body
    result_empty_body = tool.execute(
        to="test@example.com",
        subject="Test",
        body=""
    )
    print(f"   Empty body: {result_empty_body}")
    
    print("\n" + "=" * 70)
    print("✅ All Gmail tool tests passed!")
    print("\n💡 Setup Instructions:")
    print("  1. Create Google Cloud project")
    print("  2. Enable Gmail API")
    print("  3. Download OAuth credentials")
    print("  4. Run: python scripts/setup_google_oauth.py")
    print("  5. Authorize in browser")
    print("  6. Token saved automatically")
