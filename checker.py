#!/usr/bin/env python3
"""
IEEE ICONAT 2025 Proceedings Monitor

Monitors IEEE Xplore for the publication of 2025 ICONAT proceedings
and sends a one-time email notification when detected.
"""

import json
import logging
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Configuration
TARGET_URL = "https://ieeexplore.ieee.org/xpl/conhome/1845744/all-proceedings"
TARGET_YEAR = "2025"
TARGET_KEYWORD = "ICONAT"
STATE_FILE = "state.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SUBJECT = "IEEE ICONAT 2025 Proceedings Are Live"
RECIPIENT_EMAIL = "babhinay27@gmail.com"

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import Playwright for JS-rendered pages
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(
        "Playwright not available. JavaScript-rendered content may not load properly."
    )


def load_state() -> Dict[str, bool]:
    """Load state from state.json file."""
    state_file = Path(STATE_FILE)
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading state file: {e}. Creating new state.")

    # Default state if file doesn't exist or is invalid
    default_state = {"notified": False}
    save_state(default_state)
    return default_state


def save_state(state: Dict[str, bool]) -> None:
    """Save state to state.json file."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info(f"State saved: notified={state.get('notified', False)}")
    except IOError as e:
        logger.error(f"Error saving state file: {e}")
        raise


def fetch_page(url: str) -> Optional[str]:
    """Fetch the target page, using Playwright if available for JS-rendered content."""
    # Try Playwright first if available (for JS-rendered pages)
    if PLAYWRIGHT_AVAILABLE:
        try:
            logger.info(f"Fetching page with Playwright (JS rendering): {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    locale="en-US",
                )
                page = context.new_page()
                
                # Navigate with longer timeout and simpler wait strategy
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                logger.info("Page loaded, waiting for content...")
                
                # Wait for specific content to appear (year numbers like 2022, 2023, 2024)
                # Try to wait for any proceeding entry to appear
                try:
                    # Wait for text containing a year pattern
                    page.wait_for_selector("text=/202[2-4]/", timeout=10000)
                    logger.info("Found proceeding content on page")
                except Exception:
                    logger.warning("Timeout waiting for specific content, continuing anyway")
                
                # Additional wait for JS to finish
                page.wait_for_timeout(5000)
                
                html_content = page.content()
                browser.close()
                logger.info(f"Successfully fetched page with Playwright (content length: {len(html_content)})")
                return html_content
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}. Falling back to requests.")

    # Fallback to requests
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": "https://ieeexplore.ieee.org/",
        }
        logger.info(f"Fetching page with requests: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched page (status: {response.status_code})")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching page: {e}")
        return None


def parse_proceedings(html_content: str) -> List[str]:
    """
    Parse HTML to extract individual proceeding entries from the 'All Proceedings' section.

    Returns a list of proceeding entry text content.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Since the page is JS-rendered, look for any content containing ICONAT and years
        # The proceedings might be in various formats in the HTML

        entries = []

        # Strategy 1: Look for any text containing both year patterns and ICONAT
        # Search the entire page content for proceeding-like patterns
        page_text = soup.get_text(separator="\n", strip=True)

        # Look for lines/paragraphs that contain both year and conference keywords
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]

        for i, line in enumerate(lines):
            # Check if line contains a year
            has_year = any(year in line for year in ["2022", "2023", "2024", "2025"])
            # Check if line contains ICONAT or related keywords
            line_lower = line.lower()
            has_conference = any(
                keyword in line_lower
                for keyword in [
                    "iconat",
                    "international conference",
                    "conference for advancement",
                    "advancement in technology",
                ]
            )

            if has_year and has_conference:
                # Try to get the full entry (current line + next few lines if they seem related)
                entry_text = line
                # Look ahead a few lines for location or additional info
                for j in range(1, 3):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        # If next line looks like part of the entry (location, etc.)
                        if (
                            "location" in next_line.lower()
                            or len(next_line) < 100
                            or any(char.isdigit() for char in next_line[:10])
                        ):
                            entry_text += " " + next_line
                        else:
                            break
                entries.append(entry_text.strip())

        # Strategy 2: Look for specific HTML elements that might contain proceedings
        # Check for list items, divs, or spans that contain year + ICONAT
        if not entries:
            for element in soup.find_all(["li", "div", "p", "span", "article"]):
                text = element.get_text(separator=" ", strip=True)
                if len(text) > 20:  # Reasonable length for an entry
                    has_year = any(
                        year in text for year in ["2022", "2023", "2024", "2025"]
                    )
                    text_lower = text.lower()
                    has_conference = any(
                        keyword in text_lower
                        for keyword in [
                            "iconat",
                            "international conference",
                            "conference for advancement",
                        ]
                    )
                    if has_year and has_conference:
                        entries.append(text)

        # Strategy 3: Look for "All Proceedings" section specifically
        all_proceedings_section = None

        # Look for heading containing "All Proceedings"
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "a", "button"])
        for heading in headings:
            text = heading.get_text(strip=True)
            if (
                "All Proceedings" in text
                or "all-proceedings" in str(heading.get("href", "")).lower()
            ):
                # Find the parent container
                parent = heading.find_parent(["div", "section", "article", "main"])
                if parent:
                    all_proceedings_section = parent
                    break

        # If we found the section, extract entries from it
        if all_proceedings_section:
            section_entries = []
            for element in all_proceedings_section.find_all(["li", "div", "p"]):
                text = element.get_text(separator=" ", strip=True)
                if len(text) > 20:
                    if any(year in text for year in ["2022", "2023", "2024", "2025"]):
                        section_entries.append(text)
            if section_entries:
                entries.extend(section_entries)

        # Remove duplicates while preserving order
        seen = set()
        unique_entries = []
        for entry in entries:
            entry_key = entry.lower()[:100]  # Use first 100 chars as key
            if entry_key not in seen:
                seen.add(entry_key)
                unique_entries.append(entry)

        if not unique_entries:
            logger.warning("Could not find any proceeding entries in the page")
            logger.debug(
                f"Page content length: {len(html_content)}, Text length: {len(page_text)}"
            )
            # Log a sample of the page text for debugging
            if page_text:
                # Log first 30 lines to help debug
                sample_lines = lines[:30] if len(lines) > 30 else lines
                logger.info("First 30 lines of page text:")
                for i, line in enumerate(sample_lines):
                    logger.info(f"  Line {i}: {line[:150]}")
            return []

        logger.info(f"Found {len(unique_entries)} proceeding entries")
        # Log the entries for debugging
        for i, entry in enumerate(unique_entries):
            logger.info(f"  Entry {i+1}: {entry[:200]}")
        return unique_entries

    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return []


def check_for_2025_iconat(entries: List[str]) -> Optional[str]:
    """
    Check if any proceeding entry contains both '2025' and 'ICONAT' in the same entry.

    Returns the matching entry text if found, None otherwise.
    """
    for entry in entries:
        entry_lower = entry.lower()
        # Check if both target year and keyword appear in the same entry
        if TARGET_YEAR in entry and TARGET_KEYWORD.lower() in entry_lower:
            logger.info(f"Found matching entry: {entry[:100]}...")
            return entry

    logger.info("No matching entry found (2025 + ICONAT)")
    return None


def send_notification(proceeding_entry: str) -> bool:
    """
    Send email notification via Gmail SMTP.

    Returns True if email was sent successfully, False otherwise.
    """
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_APP_PASSWORD")

    if not email_address or not email_password:
        logger.error("Email credentials not found in environment variables")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_address
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = EMAIL_SUBJECT

        # Create email body
        body = f"""IEEE ICONAT 2025 Proceedings Are Now Available!

Conference: International Conference for Advancement in Technology (ICONAT)
Year: 2025

Proceedings URL: {TARGET_URL}

Detected Entry:
{proceeding_entry}

---
This is an automated notification from the IEEE ICONAT 2025 monitoring agent.
"""

        msg.attach(MIMEText(body, "plain"))

        # Send email
        logger.info(f"Sending email to {RECIPIENT_EMAIL}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)

        logger.info("Email sent successfully")
        return True

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def main() -> int:
    """Main function to orchestrate the monitoring process."""
    try:
        # Load state
        state = load_state()

        # Check if already notified
        if state.get("notified", False):
            logger.info("Already notified. Exiting silently.")
            return 0

        # Fetch page
        html_content = fetch_page(TARGET_URL)
        if not html_content:
            logger.error("Failed to fetch page. Exiting.")
            return 1

        # Parse proceedings
        entries = parse_proceedings(html_content)
        if not entries:
            logger.warning("No proceeding entries found. Exiting.")
            return 0

        # Check for 2025 ICONAT
        matching_entry = check_for_2025_iconat(entries)
        if not matching_entry:
            logger.info("2025 ICONAT proceedings not yet published. Exiting.")
            return 0

        # Send notification
        email_sent = send_notification(matching_entry)
        if email_sent:
            # Update state
            state["notified"] = True
            save_state(state)
            logger.info("Notification sent and state updated successfully")
            return 0
        else:
            # Even if email fails, update state to prevent retry loops
            # But log the error
            logger.error(
                "Email sending failed, but updating state to prevent retry loops"
            )
            state["notified"] = True
            save_state(state)
            return 1

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
