# 🧹 TG Cleaner (Telegram Workspace Cleanup Tool)

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=flat-sq)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat-sq&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Telethon](https://img.shields.io/badge/Telethon-1.36.0-26A69A?style=flat-sq)](https://github.com/LonamiWebs/Telethon)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.30-red?style=flat-sq)](https://www.sqlalchemy.org/)
[![UI Style](https://img.shields.io/badge/UI-Glassmorphism_Dark-blueviolet?style=flat-sq)](https://fonts.google.com/specimen/Inter)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-sq)](LICENSE)

A production-grade, highly responsive web application designed to safely, selectively, and bulk clean up unwanted Telegram groups, channels, supergroups, and bots. 

Built using a modern asynchronous stack with **FastAPI**, **Telethon (MTProto Client)**, **SQLAlchemy**, and a premium dark glassmorphism user interface styled with **Inter** typography and animated custom CSS brand marks.

---

## 📖 Table of Contents
1. [✨ Key Features](#-key-features)
2. [📁 Repository Structure](#-repository-structure)
3. [📊 Database Schema & Architecture](#-database-schema--architecture)
4. [🚀 Installation & Quick Start](#-installation--quick-start)
5. [🔑 Obtaining Telegram API Credentials](#-obtaining-telegram-api-credentials)
6. [🖥️ Detailed Usage Walkthrough](#%EF%B8%8F-detailed-usage-walkthrough)
7. [🔒 Security & Session Isolation](#-security--session-isolation)
8. [⚠️ Telegram Rate Limits & Safety (FloodWait)](#-telegram-rate-limits--safety-floodwait)
9. [🔧 Troubleshooting & FAQ](#-troubleshooting--faq)
10. [📦 Technology Stack](#-technology-stack)
11. [📄 License & Disclaimer](#-license--disclaimer)

---

## ✨ Key Features

### 🔐 Secure MTProto Authentication
* Log in directly via the official Telegram MTProto protocol using your **API ID**, **API Hash**, and **Phone Number**.
* Support for **OTP verification code entry** and **Two-Factor Authentication (2FA)** cloud passwords.
* Generates a Telethon `StringSession` stored locally in your SQLite database. **Your account password and credentials are never sent to third parties or stored on external servers.**

### 📊 Interactive Dashboard
* **Real-time Stats Grid**: Displays total group/channel counts, chats scheduled for removal, and protected chats in your Keep List.
* **Insights Widgets**: Features a circular progress gauge representing cleanup ratios and bar charts showing chat distribution by type (Groups, Channels, Personal Chats, Bots).
* **Smart Filter Chips**: Filter chats dynamically by type (Groups, Channels, Supergroups, Bots, Personal), or tags (Muted, Unread, Inactive, Archived, Kept, To Remove).
* **Multifunctional Search & Sort**: Search chats instantly by name or username, and sort by Newest Activity, Oldest Activity, Name (A-Z), Member Count, or Unread Count.
* **Bulk Export**: Download your Keep List as a formatted **CSV** or styled **Excel (.xlsx)** spreadsheet using the top menu before executing a cleanup.

### 🎚️ Custom Inactivity Threshold Dropdown
* Customize what constitutes an "inactive" chat directly from the dashboard (choose from **7, 14, 30, 90, or 180 days** of inactivity).
* Instantly updates the **💤 Inactive** filter tab counts and the **⚡ Quick Actions Checklist** labels dynamically.

### 📋 Interactive Cleanup Preview
* Review the exact list of chats to leave on the **Cleanup Engine** page before executing.
* **Interactive Checkboxes**: Uncheck any chat to protect it (syncs with the DB keep-list in real-time). The UI visually dims/strikes through the chat, updates stats dynamically, and disables the cleanup trigger if `0` chats are scheduled to leave.

### 🚀 Asynchronous Stream Engine & Single-Run Logging
* Real-time progress updates streamed directly to the UI using **Server-Sent Events (SSE)**.
* **Emergency Stop**: Cancel the cleanup operation mid-run at any time.
* **Single-Run Completion Logs**: The final log container purges previous run histories and displays the left/failed status of the *current* execution only.

### 📱 Premium, Responsive Design
* **Glassmorphism Theme**: Sleek dark UI with harmonious color palettes, subtle gradients, and tactile hover translations.
* **Inter Typography**: Loaded from Google Fonts for clean, readable text layouts.
* **Mobile-friendly Header Grid**: Adaptive layout wraps cleanly into a 2x2 grid block on mobile viewports.
* **Responsive Chat List Items**: The avatar, title, and actions wrap onto two rows on mobile viewports so that the Keep buttons are never cut off.
* **Smooth Back-to-Top Button**: A floating, animated arrow button appears dynamically when scrolling down long lists.

---

## 📁 Repository Structure

The repository contains the FastAPI code organized in a clean, modular structure under the `telegram-cleaner` directory:

```
telegram-cleaner/                # Git repository root
├── README.md                    # Main repository documentation (this file)
└── telegram-cleaner/            # Web application directory
    ├── app/                     # Backend application code
    │   ├── __init__.py
    │   ├── database/
    │   │   └── __init__.py      # SQLAlchemy async engine + DB dependencies
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── models.py        # SQLite database models (UserSession, ChatRecord, CleanupLog)
    │   ├── routes/
    │   │   ├── __init__.py
    │   │   ├── auth.py          # Authentication endpoints (/api/auth/*)
    │   │   ├── dashboard.py     # Dashboard controls and export endpoints (/api/dashboard/*)
    │   │   └── cleanup.py       # Stream and cleanup routes (/api/cleanup/*)
    │   └── services/
    │       ├── __init__.py
    │       ├── telegram.py      # Telethon MTProto wrapper (Auth, Dialogs Fetch, Chat Leave)
    │       └── session.py       # DB session retrieval utilities
    ├── static/                  # Frontend static assets
    │   ├── css/
    │   │   └── main.css         # Glassmorphic dark/light styles, animations, responsive queries
    │   └── js/
    │       └── utils.js         # Shared JS helpers (Toasts, Date formatters, Back-to-Top injector)
    ├── templates/               # HTML Jinja2 templates
    │   ├── index.html           # 3-Step Wizard login template
    │   ├── dashboard.html       # Main chat filters, stats charts, and checklists
    │   └── cleanup.html         # Preview checkboxes, running stream logs, and done summaries
    ├── database/                # Directory auto-created for SQLite databases (gitignored)
    ├── main.py                  # FastAPI core entry point
    ├── requirements.txt         # Python dependencies
    ├── .env.example             # Environment variable templates
    └── README.md                # Subfolder documentation
```

---

## 📊 Database Schema & Architecture

The database is powered by SQLite via SQLAlchemy's asynchronous extension (`aiosqlite`). It consists of three main tables:

### 1. `UserSession`
Stores active client configurations and Telethon session strings.
* `session_id` (String, Primary Key): Secure browser-side session identifier (stored in `localStorage`).
* `phone` (String): Logged-in phone number.
* `session_string` (Text): Telethon StringSession string for authorization.
* `api_id` (Integer): Telegram Application ID.
* `api_hash` (String): Telegram Application Hash.
* `is_active` (Boolean): Active state flag.

### 2. `ChatRecord`
Caches the dialogs fetched from Telegram to support local searching, sorting, and filter chips.
* `chat_id` (BigInteger, Primary Key): Unique Telegram ID.
* `name` (String): Chat title.
* `chat_type` (String): group, channel, supergroup, megagroup, user, bot.
* `member_count` (Integer): Total members in the chat.
* `unread_count` (Integer): Total unread messages.
* `is_muted` (Boolean): Mute status.
* `is_archived` (Boolean): Archive status.
* `is_kept` (Boolean): Protected status (True = do not clean up).
* `last_activity` (DateTime): ISO date of the last message in the dialog.

### 3. `CleanupLog`
Retains logs of left/failed chats for the current run.
* `id` (Integer, Primary Key): Auto-incremented identifier.
* `chat_name` (String): Name of the processed chat.
* `action` (String): `left`, `failed`, or `skipped`.
* `error_message` (Text): Details of the failure (e.g. rate limits).
* `performed_at` (DateTime): Completed timestamp.

---

## 🚀 Installation & Quick Start

### Prerequisites
* **Python 3.9** or higher.
* An active **Telegram Account**.
* Telegram **API ID** and **API Hash** (see [Obtaining Telegram API Credentials](#-obtaining-telegram-api-credentials) below).

### 1. Clone the Repository
Clone this repository to your local machine:
```bash
git clone https://github.com/yourusername/telegram-cleaner.git
cd telegram-cleaner
```

### 2. Set Up Virtual Environment
Navigate to the web application directory and create a Python virtual environment:
```bash
# Move into the web app folder
cd telegram-cleaner

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell/CMD):
.venv\Scripts\activate
# On Linux/MacOS:
source .venv/bin/activate
```

### 3. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
# On Windows (PowerShell):
copy .env.example .env

# On Linux/MacOS:
cp .env.example .env
```
Open the `.env` file and set a custom `SECRET_KEY` for session security if desired:
```env
SECRET_KEY=your-super-secret-key-here
HOST=0.0.0.0
PORT=8000
```

### 5. Run the Application
Start the Uvicorn server to run the application locally:
```bash
python main.py
# OR
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## 🔑 Obtaining Telegram API Credentials

TG Cleaner uses the official Telegram API. You must generate credentials to authorize the MTProto client:

1. Visit **[https://my.telegram.org/apps](https://my.telegram.org/apps)**.
2. Enter your phone number in international format (e.g., `+1234567890`) and submit.
3. Copy the confirmation code sent directly to your Telegram chat app, paste it on the website, and log in.
4. Select **API development tools**.
5. Fill in the **Create new application** form:
   * **App title**: Any name (e.g. `MyCleanerApp`).
   * **Short name**: Short alphanumeric slug (e.g. `mycleaner`).
   * **URL/Description**: Can be left blank or set to default.
6. Click **Create application**.
7. Copy the displayed **App api_id** (integer) and **App api_hash** (string). These will be input on the TG Cleaner login page.

---

## 🖥️ Detailed Usage Walkthrough

### Step 1: Log In & Connect
1. Enter your **API ID**, **API Hash**, and **Phone Number** on the landing page.
2. Click **Request Code**. The backend will initiate a connection with Telegram.
3. Check your Telegram app for the verification code. Enter it on the page.
4. If your account has **Two-Factor Authentication (2FA)** active, enter your Cloud Password when prompted.
5. Click **Verify Code** to redirect to the Dashboard.

### Step 2: Configure and Keep Chats
1. **Interactive Directory**: All your Telegram groups, channels, supergroups, and bots will load on the dashboard.
2. **Mark to Keep**: All loaded chats are marked for removal by default. Identify chats you want to retain and click **Keep** (which lights up a green active badge).
3. **Filtering**: Use filter tabs like **Muted**, **Unread**, **Inactive**, **Archived**, or search by name to quickly find items.
4. **Quick Actions Checklist**: Toggle predefined rules on the sidebar:
   * Leave Muted Chats
   * Leave Inactive Chats (configured by the threshold dropdown)
   * Leave Chats with 0 Unread messages
   * Leave Channels only / Leave Groups only / Leave Bots only
5. **Export Backups**: Click **Export CSV** or **Export Excel** in the header to download a copy of your Kept list before starting cleanup.

### Step 3: Review and Run Cleanup
1. Click the **Cleanup** link in the navigation header.
2. Review the preview list. You can check/uncheck items dynamically to keep or remove them.
3. Use the **Delay Slider** (between 1.0s and 15.0s) to choose your request spacing. *A delay of 2.0s or higher is recommended to avoid rate limits.*
4. Click **Start Cleanup**. Confirm the prompt.
5. View real-time SSE stream outputs showing successful leaves, skips, or failures.
6. If you need to stop, click the **Emergency Stop** button.

---

## 🔒 Security & Session Isolation

* **No Password Retention**: TG Cleaner does not store your Telegram account password or API keys on any cloud server. Your credentials and auth tokens are saved locally on your computer in an SQLite database.
* **StringSession Authentication**: During authentication, Telethon requests a secure authorization string from Telegram. This `StringSession` is cached in your SQLite file.
* **UUID Isolation**: When you log in, the application assigns a unique UUID session token stored in your browser's `localStorage` (`tg_cleaner_session`). All API requests verify this token locally to prevent session hijacking.

---

## ⚠️ Telegram Rate Limits & Safety (FloodWait)

Telegram places limits on how quickly you can leave chats to prevent spam.
* **Default Spacing**: The application uses a default **2.0s** delay between leave operations.
* **FloodWait Protection**: If Telegram issues a rate limit error (`FloodWaitError`), the application catches the event, extracts the sleep duration, suspends the cleanup automatically, and resumes after the cool-down period.
* **Recommendation**: If leaving more than 100 chats, set the delay to **3.0s - 5.0s** to maintain account health.

---

## 🔧 Troubleshooting & FAQ

#### 1. Why am I getting a `FloodWait` error?
You are leaving too many channels/groups too quickly. Increase the cleanup delay slider to **3.0s** or higher.

#### 2. The login hangs at "Requesting Code..."
Verify that your **API ID** and **API Hash** are correct and match your developer credentials on `my.telegram.org`. Also, ensure you enter your phone number in full international format (e.g. `+447911123456`).

#### 3. Database is locked error (`OperationalError: database is locked`)
This can happen if multiple instances of Uvicorn are running simultaneously or a query is frozen. Close all terminal instances, stop the server, and restart it.

#### 4. Can I recover a channel/group after leaving it?
No. Once the tool leaves a group or channel, it is permanent. If you want to join again, you will need a public join link or an invite. Please use the **Cleanup Preview** carefully.

---

## 📦 Technology Stack

* **Backend**: FastAPI (Asynchronous Web Framework)
* **ASGI Server**: Uvicorn
* **Telegram Client**: Telethon (Asynchronous MTProto wrapper)
* **ORM & Database**: SQLAlchemy (Async) + aiosqlite (SQLite)
* **Frontend**: Vanilla HTML5, Javascript (ES6+), CSS Grid/Flexbox
* **Excel Engine**: Openpyxl
* **Fonts**: Inter (Google Fonts)

---

## 📄 License & Disclaimer

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

**Disclaimer**: This application is not officially associated with Telegram Messenger. Leaving channels/groups in bulk is permanent. Use this tool responsibly and review your preview lists carefully before running cleanup.
