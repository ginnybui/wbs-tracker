# 📂 WBS Tracker Pro

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35.0-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API%20v4-34A853?style=flat-square&logo=google-sheets&logoColor=white)](https://developers.google.com/sheets/api)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-orange.svg?style=flat-square)](https://www.python.org/dev/peps/pep-0008/)

**WBS Tracker Pro** is a modern, intuitive, and highly interactive Work Breakdown Structure (WBS) tracking dashboard. Built using **Python & Streamlit**, it offers real-time two-way synchronization and secure integration with a **Google Sheets** database powered by Google Cloud Platform APIs.

---

## 📝 Table of Contents
1. [Key Features](#-key-features)
2. [Directory Structure](#-directory-structure)
3. [Tech Stack](#-tech-stack)
4. [Database Schema](#-database-schema)
5. [Installation & Local Setup](#-installation--local-setup)
6. [Environment Secrets Configuration](#-environment-secrets-configuration)
7. [Git Workflow](#-git-workflow)

---

## ✨ Key Features

- 💼 **Multi-Project Workspace Management**: Effortlessly switch and manage multiple isolated project workspaces dynamically from a single dashboard.
- 📦 **Secure Project Archiving (Soft Delete)**: Seamlessly toggle and archive older projects to keep your dashboard clean without losing any related historical tasks.
- ✏️ **Real-Time Inline Data Editor**: Edit task titles, statuses, progress, and logged hours directly on the interactive table grid with instant cloud database synchronization.
- 🔢 **Smart Pagination & Searching**: Highly-optimized pagination (50 records per page) synchronized with browser URL parameters (`?page=list&p=1`) to prevent status loss on refresh.
- 📊 **Automated Performance Tracking**: Real-time evaluation of task completion percentages (`% Completion`) and time efficiency (`🟢 Efficient` / `🔴 Overtime`).
- 🗑️ **Bulk Deletion Controls**: Safeguarded multi-select checkboxes coupled with confirmation dialog warnings to securely delete multiple tasks in one click.

---

## 📂 Directory Structure

Here is the folder structure tree of the project:
```text
wbs-tracker/
├── .streamlit/
│   ├── secrets.toml          # Contains GCP private key & Sheets configuration (Local)
│   └── secrets.toml.save     # Backup configuration file
├── docs/                     # Project documentation resources
├── src/
│   ├── app.py                # Main Streamlit application codebase (CRUD & UI)
│   └── index.html            # Custom HTML styling template
├── README.md                 # Project documentation
├── requirements.txt          # Declared python package dependencies
├── tasks.csv                 # Local backup database (CSV fallback)
└── venv/                     # Python Virtual Environment
```

---

## 🛠️ Tech Stack

| Technology / Library | Classification | Version | Role in the Project |
| :--- | :--- | :--- | :--- |
| **Streamlit** | Frontend Framework | `1.35.0` | Orchestrates the responsive web UI, data inputs, dialog boxes, URL routing, and active session states. |
| **Pandas** | Data Processing | `2.x` | Handles structured tabular data, quick filtering, dynamic pagination, and dataframe manipulations. |
| **gspread** | Database Integration | `6.x` | Standardized Python client to read, append, update, and clear rows on Google Sheets v4. |
| **oauth2client** | Authentication | `4.x` | Authorizes Google Cloud Platform (GCP) Service Account credentials securely. |
| **google-auth** | Security / OAuth2 | `2.x` | Manages secure protocol integrations and communication channels with Google APIs. |

---

## 📊 Database Schema

The database is split into two relational worksheets in Google Sheets to enforce database integrity and standard modeling practices:

### 1. Project Metadata Worksheet (`Projects_Metadata`)
Maintains metadata configurations for each project workspace, keyed by a unique `Project ID`.

| Column Header | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| **Project ID** | String | Primary Key (e.g., `PRJ-001`) | Unique identifier for each project |
| **Project Name** | String | Required | The display name of the project |
| **Platform** | String | Optional (iOS, Android, Web, CMS) | Intended deployment platforms |
| **Description** | String | Optional | Detailed overview and objectives of the project |
| **Start Date** | Date (YYYY-MM-DD) | Required | Project kickoff date |
| **Target End Date** | Date (YYYY-MM-DD) | Required | Estimated project delivery deadline |
| **Status** | String | Active, On Hold, Completed, Archived | Current status state of the project workspace |

### 2. WBS Tasks Worksheet (`Data_UAT` / `Data_Dev`)
Contains the full breakdown of tasks, relationally linked back to the metadata via the `Project ID` column.

| Column Header | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| **Project ID** | String | Foreign Key (References `Projects_Metadata`) | The project containing this specific task |
| **Task ID** | Integer | Primary Key (Auto-Increment) | Unique identification code for the task |
| **Title** | String | Required | Content/Title of the WBS task |
| **Health** | String | Auto-calculated (`🟢 Efficient` / `🔴 Overtime`) | Efficiency status (Overtime if Act Hours > Est Hours) |
| **Status** | String | To Do, In Progress, Done, On Hold | Execution status state of the task |
| **Est Hours** | Float | >= 0 | Estimated hours required for completion |
| **Act Hours** | Float | >= 0 | Actual hours logged on execution |
| **Start Date** | Date (YYYY-MM-DD) | Required | Kickoff date of the task |
| **End Date** | Date (YYYY-MM-DD) | Required | Deadline/completion date of the task |
| **Completion %** | Integer | 0 - 100 | Task progress (Forced to 100% if Status = Done, 0% if To Do) |

---

## 🚀 Installation & Local Setup

Execute the following commands in sequence inside your Terminal shell:

### Step 1: Clone the Repository
```bash
git clone https://github.com/ginnybui/wbs-tracker.git
cd wbs-tracker
```

### Step 2: Initialize a Python Virtual Environment (Recommended)
```bash
# Initialize venv
python3 -m venv venv

# Activate venv
# On macOS/Linux:
source venv/bin/activate
# On Windows (Command Prompt):
# venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Launch the Local Server
```bash
streamlit run src/app.py
```
The application will automatically start in your default browser at: **[http://localhost:8502](http://localhost:8502)**.

---

## 🔑 Environment Secrets Configuration

To connect the application to your Google Sheets database, you must configure a local environment file:

1. Create a directory named `.streamlit` at the root of your project directory.
2. Inside `.streamlit/`, create a file named `secrets.toml`.
3. Open `secrets.toml` and configure your GCP Service Account keys and Google Sheet URLs using the template below:

```toml
[gcp]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "your-private-key-id"
private_key = "BASE64_ENCODED_PRIVATE_KEY_OR_RAW_KEY"
client_email = "your-service-account-email@gcp.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email"
universe_domain = "googleapis.com"

[gsheets]
spreadsheet_url = "https://docs.google.com/spreadsheets/d/your-spreadsheet-id-here/edit"
worksheet_name = "Data_UAT"
```

---

## 🔄 Git Workflow

This project adheres to a clean and structured branching model to keep production code safe and stable:

- **`main` Branch**: Contains the cleanest, fully-tested, highly-stable release-ready version of the code. Never commit or develop directly on `main`.
- **`dev` Branch**: Serves as the integration and internal testing sandbox branch for incoming features.
- **`feature/*` Branches**: Temporary feature-specific branches branched off from `main` or `dev` to execute isolated development tasks (e.g., `feature/update-readme`, `feature/edit-archive-project`). Once completed and fully tested locally, a Pull Request is opened to merge back into the target branch.

---
*We hope WBS Tracker Pro empowers your team's project tracking workflows!*
