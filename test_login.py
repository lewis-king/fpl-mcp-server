import asyncio
import sys
from src.fpl_server.auth import FPLAutomation

# Hardcode credentials here for the test, or input them when running
EMAIL = "someemail@example.com"
PASSWORD = "somepassword"

async def main():
    print(f"--- Starting Login Test for {EMAIL} ---")
    
    # 1. Initialize Auth
    # We use the code exactly as it exists in your project
    auth = FPLAutomation(EMAIL, PASSWORD)
    
    print("Launching browser...")
    try:
        # 2. Attempt Login
        token = await auth.login_and_get_token()
        
        # 3. Report Results
        if token:
            print("\n✅ SUCCESS!")
            print(f"Token captured: {token[:30]}...")
        else:
            print("\n❌ FAILED.")
            print("Browser closed without capturing a token.")
            
    except Exception as e:
        print(f"\n❌ CRASHED: {e}")

if __name__ == "__main__":
    if EMAIL == "your_email@example.com":
        print("Please edit test_login.py and add your actual FPL credentials.")
        sys.exit(1)
        
    asyncio.run(main())