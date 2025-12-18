# IEEE ICONAT 2025 Proceedings Monitor

An automated monitoring agent that tracks when IEEE Xplore publishes the 2025 proceedings for the International Conference for Advancement in Technology (ICONAT) and sends a one-time email notification.

## Overview

This project uses GitHub Actions to automatically check the IEEE Xplore website every 12 hours for the publication of ICONAT 2025 proceedings. When detected, it sends an email notification and updates its state to prevent duplicate notifications.

**Target Page:** https://ieeexplore.ieee.org/xpl/conhome/1845744/all-proceedings

## How It Works

1. **Scheduled Execution**: GitHub Actions runs the monitoring script every 12 hours (configurable)
2. **State Check**: The script first checks `state.json` to see if a notification has already been sent
3. **Page Fetching**: If not notified, it fetches the IEEE Xplore page with a realistic User-Agent
4. **HTML Parsing**: BeautifulSoup extracts the "All Proceedings" section and individual proceeding entries
5. **Detection**: Checks if any proceeding entry contains both "2025" and "ICONAT" in the same entry
6. **Notification**: If found, sends an email via Gmail SMTP
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

To change from 12 hours to a different interval, edit `.github/workflows/monitor.yml`:

```yaml
schedule:
  - cron: '0 */12 * * *'  # Every 12 hours
```

Common cron patterns:
- `0 */6 * * *` - Every 6 hours
- `0 */24 * * *` - Every 24 hours (once daily)
- `0 9 * * *` - Every day at 9:00 AM UTC
- `0 9,21 * * *` - Twice daily at 9:00 AM and 9:00 PM UTC

**Note:** GitHub Actions schedules may have slight delays (up to 15 minutes).

### Modifying Target URL or Keywords

Edit `checker.py`:

```python
TARGET_URL = "https://ieeexplore.ieee.org/xpl/conhome/1845744/all-proceedings"
TARGET_YEAR = "2025"
TARGET_KEYWORD = "ICONAT"
```

### Changing Email Recipient

Edit `checker.py`:

```python
RECIPIENT_EMAIL = "your-email@example.com"
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

The script:
1. Locates the "All Proceedings" section on the IEEE Xplore page
2. Extracts individual proceeding entries (each entry represents one conference year)
3. Checks each entry to see if it contains both:
   - The year "2025"
   - The keyword "ICONAT" (case-insensitive)
4. Only triggers if both appear in the **same entry** (avoiding false positives)

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

## Troubleshooting

### Email Not Sending

- Verify `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` secrets are set correctly
- Ensure 2-Step Verification is enabled on your Google Account
- Check GitHub Actions logs for specific error messages

### Script Not Finding Proceedings

- The page structure may have changed. Check the logs in GitHub Actions
- You may need to update the HTML parsing logic in `checker.py`

### Workflow Not Running

- Ensure GitHub Actions is enabled in repository settings
- Check that the cron schedule is valid
- Manual triggers via `workflow_dispatch` should always work

## Ethics & Rate Limiting

- Runs only every 12 hours (respectful frequency)
- Uses a realistic User-Agent string
- Does not bypass authentication or paywalls
- Only reads publicly available content
- Complies with IEEE Xplore terms of service

## License

This project is provided as-is for personal use. Please respect IEEE Xplore's terms of service and use responsibly.

## Support

For issues or questions, please check the GitHub Actions logs first, then open an issue in the repository.

