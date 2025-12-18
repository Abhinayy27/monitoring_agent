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
    """Fetch the target page with a realistic User-Agent."""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        logger.info(f"Fetching page: {url}")
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

        # Find the "All Proceedings" section
        # Look for common patterns: headings, divs with specific classes, or list items
        all_proceedings_section = None

        # Strategy 1: Look for heading containing "All Proceedings"
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        for heading in headings:
            if heading and "All Proceedings" in heading.get_text():
                # Find the parent container or next sibling container
                parent = heading.find_parent()
                if parent:
                    all_proceedings_section = parent
                    break

        # Strategy 2: Look for divs or sections with "All Proceedings" text
        if not all_proceedings_section:
            for div in soup.find_all(["div", "section"]):
                text = div.get_text()
                if "All Proceedings" in text:
                    all_proceedings_section = div
                    break

        if not all_proceedings_section:
            logger.warning("Could not find 'All Proceedings' section")
            return []

        # Extract individual proceeding entries
        # Each entry should contain both a year and conference-related keywords
        entries = []

        # Strategy 1: Look for list items (common pattern for proceedings lists)
        list_items = all_proceedings_section.find_all("li")
        if list_items:
            for li in list_items:
                text = li.get_text(separator=" ", strip=True)
                # Check if it looks like a proceeding entry (contains year and conference keywords)
                if text and len(text) > 10:
                    if any(year in text for year in ["2022", "2023", "2024", "2025"]):
                        entries.append(text)

        # Strategy 2: Look for divs or paragraphs that contain proceeding information
        if not entries:
            for element in all_proceedings_section.find_all(["div", "p", "article"]):
                text = element.get_text(separator=" ", strip=True)
                # Look for entries containing both a year and conference-related terms
                if (
                    text and len(text) > 20
                ):  # Longer minimum to avoid headers/navigation
                    has_year = any(
                        year in text for year in ["2022", "2023", "2024", "2025"]
                    )
                    has_conference = any(
                        keyword.lower() in text.lower()
                        for keyword in [
                            "ICONAT",
                            "International Conference",
                            "Conference for Advancement",
                        ]
                    )
                    if has_year and has_conference:
                        entries.append(text)

        # Strategy 3: Fallback - extract text blocks and filter by patterns
        if not entries:
            text_content = all_proceedings_section.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
            # Group consecutive lines that might form a complete entry
            current_entry = []
            for line in lines:
                # Check if line contains year or conference keywords
                if any(
                    indicator in line
                    for indicator in [
                        "2022",
                        "2023",
                        "2024",
                        "2025",
                        "ICONAT",
                        "iconat",
                        "International Conference",
                        "Location:",
                    ]
                ):
                    current_entry.append(line)
                    # If we have multiple lines or a substantial entry, save it
                    if len(current_entry) >= 2 or len(" ".join(current_entry)) > 30:
                        entry_text = " ".join(current_entry)
                        if any(
                            year in entry_text
                            for year in ["2022", "2023", "2024", "2025"]
                        ):
                            entries.append(entry_text)
                        current_entry = []
                elif current_entry:
                    # Non-matching line after building entry - save what we have
                    entry_text = " ".join(current_entry)
                    if any(
                        year in entry_text for year in ["2022", "2023", "2024", "2025"]
                    ):
                        entries.append(entry_text)
                    current_entry = []

            # Save any remaining entry
            if current_entry:
                entry_text = " ".join(current_entry)
                if any(year in entry_text for year in ["2022", "2023", "2024", "2025"]):
                    entries.append(entry_text)

        logger.info(f"Found {len(entries)} proceeding entries")
        return entries

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
