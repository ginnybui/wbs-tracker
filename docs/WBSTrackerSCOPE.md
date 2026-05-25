# SCOPE.md: Integrated Multi-Project WBS & CMS System

## 1. Project Objective
To develop a lightweight, web-based CMS tool for managing multiple software projects simultaneously. The system enables Project Managers (PMs) to initialize projects and assign members, while allowing team members to switch between assigned projects to track and update their work progress.

## 2. Target Users & Access Control (RBAC)
- **Admin (Project Manager):**
    - Authority to create, initialize, and delete projects.
    - Full CMS access to manage tasks and platforms (iOS, Android, Web, CMS).
    - Full visibility into all project data, including detailed effort hours.
- **Member (Internal Teammate):**
    - Access to assigned projects via a project selector.
    - Permissions to view detailed "Estimated Hours" and "Actual Hours" for internal tracking.
    - Permissions to update completion percentages and status.
- **Client (External Stakeholder):**
    - Access to specific projects for progress monitoring.
    - View-only access to high-level Dashboards (Charts and Tables).
    - **Data Restriction:** Strictly prohibited from viewing "Estimated Hours" and "Actual Hours". Only Completion Percentage (%) and Status are visible.

## 3. Functional Requirements

### 3.1. Multi-Project Dashboard
- **Project Identity:** Clear display of the "Current Project Name" on the dashboard.
- **Project Selection:** A dropdown menu for users (Members/Clients) to switch between multiple projects they are authorized to view.
- **Dual-View Support:**
    - **Table View:** Detailed WBS items (Task ID, Title, Platform, Status, Timeline).
    - **Chart View:** Graphical representation of project health and completion status.

### 3.2. Progress & Effort Monitoring (Data Privacy Logic)
- **Internal View (Admin/Member):** Displays full effort details, including "Estimated Hours" vs. "Actual Hours" for team coordination.
- **Client/External View (Summary):** Focuses strictly on the **Completion Percentage (%)** and Status to track achievement without exposing raw hour data.
- **Progress Bars:** Visual indicators representing the percentage of task completion.

### 3.3. Interactive UI & CMS Operations
- **Selection Logic:** Support row selection to trigger sub-menus for CMS actions (Available for Admin only).
- **CMS Actions:** Specialized interface for Admins to Add, Edit, or Delete tasks.
- **Auto-fill System:** Automatically retrieve existing metadata during edits to ensure data integrity.

## 4. Technical Constraints
- **Stack:** Python (Streamlit) for unified Frontend and Backend (CMS).
- **Data Layer:** Local CSV files only (No relational databases allowed).
- **Environment:** Local development on macOS with GitHub version control.

## 5. Out of Scope
- Automated external notifications (Email/Slack).
- Integration with 3rd-party project management APIs.