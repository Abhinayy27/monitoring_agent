# IEEE ICONAT 2025 Proceedings Monitor

An automated monitoring agent that tracks when IEEE Xplore publishes the 2025 proceedings for the International Conference for Advancement in Technology (ICONAT) and sends a one-time email notification.

Reason why I made this - 

## Overview

This project uses GitHub Actions to automatically check the IEEE Xplore website twice daily (00:00 and 12:00 UTC) for the publication of ICONAT 2025 proceedings. When detected, it sends an email notification and updates its state to prevent duplicate notifications.

**Target Page:** https://ieeexplore.ieee.org/xpl/conhome/1845744/all-proceedings (In my case)

**Email Recipient:** xxxxx@email.com

## How It Works

1. **Scheduled Execution**: GitHub Actions runs the monitoring script twice daily at **00:00 UTC (midnight)** and **12:00 UTC (noon)**
2. **State Check**: The script first checks `state.json` to see if a notification has already been sent
3. **Page Fetching**: Uses **Playwright (headless browser)** to render JavaScript content and fetch the IEEE Xplore page. Falls back to `requests` if Playwright fails.
4. **HTML Parsing**: BeautifulSoup extracts individual proceeding entries from the rendered page content
5. **Detection**: Checks if any proceeding entry contains both "2025" and "ICONAT" in the same entry (e.g., "2025 4th International Conference for Advancement in Technology (ICONAT)")
6. **Notification**: If found, sends an email via Gmail SMTP to `xxxxxx@email.com`
7. **State Update**: Updates `state.json` to mark as notified and commits it back to the repository

## Setup Instructions

### 1. Clone or Fork This Repository

```bash
git clone <your-repo-url>
cd monitoring_agent
```

### 2. Set Up GitHub Secrets

You need to add two secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

   - **Name:** `EMAIL_ADDRESS`
     - **Value:** Your Gmail address (e.g., `yourname@gmail.com`)

   - **Name:** `EMAIL_APP_PASSWORD`
     - **Value:** Your Gmail App Password (see below)

### 3. Get Gmail App Password

Since Gmail requires app-specific passwords for SMTP:

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable it if not already enabled)
3. Scroll down to **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter a name like "IEEE Monitor" and click **Generate**
6. Copy the 16-character password (spaces don't matter)
7. Use this as your `EMAIL_APP_PASSWORD` secret

### 4. Enable GitHub Actions

GitHub Actions should be enabled by default. If not:

1. Go to **Settings** → **Actions**
2. Ensure **Allow all actions and reusable workflows** is selected

### 5. Test the Workflow

You can manually trigger the workflow:

1. Go to **Actions** tab in your repository
2. Select **IEEE ICONAT 2025 Monitor** workflow
3. Click **Run workflow** → **Run workflow**

## Configuration

### Changing the Schedule Frequency

The default schedule runs **twice daily** at specific times: **00:00 UTC** (midnight) and **12:00 UTC** (noon).

To change the schedule, edit `.github/workflows/monitor.yml`:

```yaml
schedule:
  - cron: '0 */12 * * *'  # Twice daily at 00:00 and 12:00 UTC
```

Common cron patterns:
- `0 */6 * * *` - Four times daily (00:00, 06:00, 12:00, 18:00 UTC)
- `0 */24 * * *` - Once daily at 00:00 UTC
- `0 9 * * *` - Once daily at 9:00 AM UTC
- `0 9,21 * * *` - Twice daily at 9:00 AM and 9:00 PM UTC
- `0 0,6,12,18 * * *` - Four times daily at specific hours

**Important:** Cron schedules run at **specific UTC times**, not X hours from the last run. GitHub Actions may have slight delays (up to 15 minutes).

### Modifying Target URL or Keywords

Edit `checker.py`:

```python
TARGET_URL = "https://ieeexplore.ieee.org/xpl/conhome/1845744/all-proceedings"
TARGET_YEAR = "2025"
TARGET_KEYWORD = "ICONAT"
```

### Changing Email Recipient

Edit `checker.py` and change the recipient:

```python
RECIPIENT_EMAIL = "xxxxx@email.com"  # Current recipient
```

## File Structure

```
monitoring_agent/
├── checker.py                 # Main monitoring script
├── requirements.txt           # Python dependencies
├── state.json                 # State tracking (git-tracked, auto-updated)
├── README.md                  # This file
└── .github/
    └── workflows/
        └── monitor.yml        # GitHub Actions workflow definition
```

## How Detection Works

### JavaScript Rendering
The IEEE Xplore page is heavily JavaScript-dependent, so the script uses **Playwright** (a headless browser) to:
- Render the page as a real browser would
- Wait for JavaScript content to load
- Extract the fully-rendered HTML

If Playwright fails or isn't available, the script falls back to standard HTTP requests.

### Detection Logic
The script:
1. Searches the entire rendered page for proceeding entries
2. Extracts individual proceeding entries (each entry represents one conference year)
3. Checks each entry to see if it contains both:
   - The year "2025"
   - The keyword "ICONAT" (case-insensitive)
4. Only triggers if both appear in the **same entry** (avoiding false positives)

Example of what it's looking for:
```
2025 4th International Conference for Advancement in Technology (ICONAT)
Location: GOA, India
```

## State Management

The `state.json` file tracks whether a notification has been sent:

```json
{
  "notified": false
}
```

When a notification is sent, it updates to:
```json
{
  "notified": true
}
```

This prevents duplicate notifications. The file is automatically committed back to the repository when updated.

## Technical Details

### Dependencies
- **requests**: For HTTP requests (fallback method)
- **beautifulsoup4**: For HTML parsing
- **lxml**: Parser backend for BeautifulSoup
- **playwright**: Headless browser for JavaScript rendering

### Workflow Steps
GitHub Actions performs these steps:
1. Checkout the repository
2. Set up Python 3.11
3. Install Python dependencies (`pip install -r requirements.txt`)
4. Install Playwright browsers (`playwright install chromium`)
5. Run `checker.py` with email credentials from GitHub Secrets
6. If `state.json` is modified, commit and push it back to the repository

## Troubleshooting

### Email Not Sending

- Verify `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` secrets are set correctly in GitHub repository settings
- Ensure 2-Step Verification is enabled on your Google Account
- Verify the App Password was generated correctly (16 characters)
- Check GitHub Actions logs for specific error messages

### Script Not Finding Proceedings

- Check GitHub Actions logs for the "Found X proceeding entries" message
- The script currently detects 2024, 2023, and 2022 ICONAT proceedings successfully
- If the page structure changes significantly, you may need to update the parsing logic in `checker.py`
- Playwright timeout errors mean the page took too long to load (try increasing the timeout in `fetch_page()`)

### Workflow Not Running

- Ensure GitHub Actions is enabled in repository settings
- The workflow runs at **00:00 UTC** and **12:00 UTC** (convert to your local timezone)
- Check that the cron schedule is valid
- Manual triggers via `workflow_dispatch` should always work (Actions tab → Run workflow)
- GitHub may delay scheduled runs by up to 15 minutes during high load

### Playwright Installation Issues

If Playwright fails to install in GitHub Actions:
- The workflow automatically installs Playwright browsers
- If it fails, check the "Install Playwright browsers" step in the workflow logs
- The script will fall back to `requests` (which won't render JavaScript content)

## Ethics & Rate Limiting

- Runs only twice per day (very respectful frequency)
- Uses a realistic User-Agent string
- Does not bypass authentication or paywalls
- Only reads publicly available content
- Uses appropriate wait times for JavaScript content to load
- Complies with IEEE Xplore terms of service

## Current Status

✅ **Active and Monitoring**
- Currently monitoring for: **2025 4th International Conference for Advancement in Technology (ICONAT)**
- Successfully detecting: 2024, 2023, and 2022 ICONAT proceedings
- Email notifications will be sent to: `xxxxxx@email.com`
- Next scheduled runs: **00:00 UTC** and **12:00 UTC** daily

## License

This project is provided as-is for personal use. Please respect IEEE Xplore's terms of service and use responsibly.

## Support

For issues or questions, please check the GitHub Actions logs first, then open an issue in the repository.

