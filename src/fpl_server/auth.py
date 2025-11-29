import logging
import asyncio
from typing import Optional, List
from playwright.async_api import async_playwright

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fpl_auth")

class FPLAutomation:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.api_token: Optional[str] = None
        self.base_url = "https://fantasy.premierleague.com"

    async def login_and_get_token(self) -> Optional[str]:
        async with async_playwright() as p:
            # Launch browser (set headless=False if you want to watch it debug)
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # 1. Setup Token Listener
            async def handle_response(response):
                if "/as/token" in response.url and response.request.method == "POST":
                    try:
                        data = await response.json()
                        if "access_token" in data:
                            self.api_token = f"Bearer {data['access_token']}"
                            logger.info("Captured API Token!")
                    except Exception:
                        pass

            page.on("response", handle_response)
            
            try:
                logger.info(f"Navigating to {self.base_url}")
                await page.goto(self.base_url)
                await page.wait_for_load_state("networkidle")
                
                # 2. Handle Cookie Banner (Robust)
                try:
                    cookie_btn = await page.wait_for_selector('#onetrust-accept-btn-handler', timeout=5000)
                    if cookie_btn:
                        await cookie_btn.click()
                        logger.info("Accepted Cookies")
                        await page.wait_for_timeout(1000)
                except Exception:
                    logger.info("No cookie banner found (or already accepted)")

                # 3. Find Login Button (Try Multiple Selectors)
                logger.info("Looking for Login button...")
                login_selectors = [
                    'button:has-text("Log in")',
                    'a:has-text("Log in")', 
                    'button:has-text("Sign in")',
                    'a:has-text("Sign in")',
                    '[data-cy="login"]',
                    '.login-button',
                    'button[class*="login"]',
                    'a[href*="login"]'
                ]
                
                login_clicked = False
                for selector in login_selectors:
                    try:
                        # Short timeout for checking each selector
                        btn = await page.wait_for_selector(selector, state="visible", timeout=2000)
                        if btn:
                            await btn.click()
                            logger.info(f"Clicked login using selector: {selector}")
                            login_clicked = True
                            break
                    except Exception:
                        continue
                
                if not login_clicked:
                    logger.error("Could not find any login button")
                    return None

                # CRITICAL FIX: Wait for navigation after clicking login
                # This matches your working code which waits for networkidle here
                logger.info("Waiting for login page navigation...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    logger.warning("Network idle timeout - continuing anyway...")

                # 4. Fill Credentials (Try Multiple Input Selectors from your working code)
                logger.info("Looking for email input...")
                
                # Email
                email_input = None
                email_selectors = [
                    'input[name="email"]',
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                    'input[id*="email" i]',
                    '#email',
                    '[data-cy="email"]'
                ]
                
                for sel in email_selectors:
                    try:
                        email_input = await page.wait_for_selector(sel, state="visible", timeout=3000)
                        if email_input:
                            logger.info(f"Found email input using: {sel}")
                            await email_input.fill(self.email)
                            break
                    except: continue

                if not email_input:
                    logger.error("Failed to find email field")
                    # Take screenshot for debugging
                    await page.screenshot(path="email_fail.png")
                    return None

                # Password
                pass_input = None
                pass_selectors = [
                    'input[name="password"]', 
                    'input[type="password"]', 
                    '#password', 
                    '[data-cy="password"]',
                    'input[placeholder*="password" i]'
                ]
                for sel in pass_selectors:
                    try:
                        pass_input = await page.wait_for_selector(sel, state="visible", timeout=3000)
                        if pass_input:
                            await pass_input.fill(self.password)
                            logger.info(f"Filled password using {sel}")
                            break
                    except: continue

                if not pass_input:
                    logger.error("Failed to find password field")
                    return None

                # 5. Submit (Try Multiple Buttons)
                submit_selectors = [
                    'button[type="submit"]', 
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    'input[type="submit"]',
                    '#btnSignIn', 
                    '[data-cy="signin"]',
                    'button[class*="signin"]',
                    'button[class*="login"]'
                ]
                for sel in submit_selectors:
                    try:
                        btn = await page.wait_for_selector(sel, state="visible", timeout=3000)
                        if btn:
                            await btn.click()
                            logger.info(f"Clicked Submit using {sel}")
                            break
                    except: continue

                # 6. Wait for Token Capture
                logger.info("Waiting for token capture...")
                # We give it up to 15 seconds to finish the API call
                for _ in range(15):
                    if self.api_token:
                        return self.api_token
                    await asyncio.sleep(1)
                
                logger.error("Login flow finished but no token captured.")
                return None

            except Exception as e:
                logger.error(f"Auth Critical Error: {e}")
                return None
            finally:
                await browser.close()