# PLAN.md: Implementation Roadmap

## Phase 1: Core Interface & Full CRUD (CURRENT FOCUS)
- [x] Initialize project structure and local CSV data layer.
- [x] Build Dashboard UI with interactive data tables.
- [ ] **Implement "Add Task" Functionality:**
    - Create a form to input new task details (Title, Status, Timeline, etc.).
    - Logic to automatically generate a unique Task ID.
    - Save new entries directly to the `tasks.csv` file.
- [ ] **Finalize "Edit Task" Logic:**
    - Enable row selection to trigger an edit form populated with existing data (Auto-fill).
    - Update and overwrite the specific row in the CSV file.
- [ ] **Finalize "Delete Task" Logic:**
    - Add a confirmation prompt to prevent accidental deletion.
    - Remove the selected row from the CSV and refresh the Dashboard.
- [ ] **Data Validation:** Ensure no empty fields for Task Title and valid percentage ranges (0-100%).

## Phase 2: Multi-Project & Platform Integration
- **Objective:** Support multiple projects and categorize by platform.
- [ ] **Data Schema Expansion:** Add columns `Project_ID`, `Project_Name`, `Platform` (iOS/Android/Web/CMS), and `Assigned_User`.
- [ ] **Admin Project Creator:** A dedicated interface for PMs to create and initialize new projects.
- [ ] **Project Selector:** Dropdown menu to switch between different project contexts.

## Phase 3: Authentication & Role-Based Access Control (RBAC)
- **Objective:** Secure access for Admin, Member, and Client.
- [ ] **Role Management:** Admin (Full access), Member (View/Update hours), Client (View-only progress).
- [ ] **Data Privacy Filters:**
    - **Internal (Admin/Member):** Show "Estimated vs. Actual Hours".
    - **External (Client):** Hide all hour data; only show Completion % and Status.

## Phase 4: Visualization & Reporting
- **Objective:** Transform data into visual charts.
- [ ] **Dual-View Switch:** Toggle between Table View and Chart View.
- [ ] **Visual Metrics:** Status distribution (Pie chart) and Platform progress (Bar chart).

## Phase 5: Finalization
- [ ] End-to-end testing of the CRUD flow for all user roles.
- [ ] Finalize documentation and GitHub repository.