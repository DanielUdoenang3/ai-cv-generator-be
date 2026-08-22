# Backend Gaps Audit — AI CV Generator

This document provides a professional audit of the FastAPI backend codebase against the features displayed in the admin dashboard user interface screenshots and the requirements outlined in the Project Requirement Document (PRD).

---

## 1. Executive Summary
While the current backend implements the core security, client submission, and chat features, there are several major modules, database tables, and API endpoints visible in the frontend UI or required by the PRD that are **completely missing** from the backend. 

To bridge this gap and make the application production-ready, the backend needs additions in:
1. **Task Management** (Kanban board cards, priorities, deadlines).
2. **Dashboard Metrics** (statistics cards on the main landing page).
3. **Staff Management** (listing and managing sub-admins/moderators).
4. **AI Prompt Management** (CRUD operations and versioning for system prompts).
5. **Document Rendering & Storage** (generating and storing PDF/Word versions of the CV).
6. **Submissions Features** (serial ID generation, deletion, and CSV exporting).

---

## 2. Gaps Identified from Frontend UI Screenshots

### 2.1 Task Management System (100% Missing)
* **What is in the UI:** 
  * A full "My Tasks" section on the sidebar.
  * A Kanban board with columns: `To Do`, `In Progress`, `Review`, `Done`.
  * Metric cards: "Total Tasks", "My Tasks", "Overdue".
  * Custom task cards showing: Task title, description, assigned staff member, deadline date (e.g., "Jan 18"), associated submission ID, and priority badge (`HIGH`, `NORMAL`).
  * A "New Task" button to create and assign tasks manually.
* **What is in the backend:** 
  * There are **no database tables** for tasks.
  * There are **no task-related schemas, controllers, or API routers**.
* **Fix needed:** 
  * Create a `Task` model in the database linked to `admins` (assignee) and `submissions`.
  * Add a `TaskPriority` enum (`low`, `normal`, `high`) and a `TaskStatus` enum (`todo`, `in_progress`, `review`, `done`).
  * Implement CRUD endpoints for tasks (`GET /api/v1/admin/tasks`, `POST /api/v1/admin/tasks`, `PATCH /api/v1/admin/tasks/{id}`).

### 2.2 Dashboard Analytics & Metrics (Missing)
* **What is in the UI:** 
  * Four stat cards: "New Requests" (+12% weekly), "In Progress" (+8% active), "Completed" (+24% monthly), and "Active Chats" (response time tracking).
  * A "Recent Submissions" preview table showing the 5 latest entries.
* **What is in the backend:** 
  * No endpoint exists to calculate these aggregated statistics.
* **Fix needed:** 
  * Create a dashboard analytics endpoint: `GET /api/v1/admin/dashboard/stats`.
  * This endpoint should perform database counts on submissions by status and count messages/active conversations, returning standard JSON for the cards.

### 2.3 Staff Management UI Support (Partial Gap)
* **What is in the UI:** 
  * A "Staff" link under the Management sidebar section.
  * An "Assigned To" dropdown filter on the submissions list where the admin can select from a list of active staff members.
* **What is in the backend:** 
  * The backend only has routes for creating an admin (`/create-admin`) and logging in. It lacks any way to **retrieve a list** of all active staff members.
* **Fix needed:** 
  * Implement a `GET /api/v1/admin/auth/staff` or `GET /api/v1/admin/staff` endpoint (restricted to `super_admin`) to return a list of active admins (`id`, `first_name`, `last_name`, `role`).

### 2.4 Prompts Management (100% Missing)
* **What is in the UI:** 
  * A "Prompts" link under the Management sidebar section.
* **What is in the backend:** 
  * No database model or API routes exist to view, update, version, or toggle active system prompts used for AI generation.
* **Fix needed:** 
  * Create a `Prompt` database model: `id`, `name`, `content` (the system text), `version`, `is_active`, `created_by`, `created_at`.
  * Implement API routes to list prompts, create versions, and toggle which prompt is currently "active" for the CV generation script.

### 2.5 Submissions UI Enhancements (Missing Features)
* **Custom Reference IDs:** The UI lists submissions with clean, custom formats (e.g., `SUB-2024-010`). The backend currently uses standard UUIDs as primary keys and has no short-code/serial code generator.
* **Submission Deletion:** The UI lists a trash bin icon in the Actions column for each submission. The backend does not have a `DELETE /submissions/{id}` route.
* **Export Action:** The UI has an "Export" action button. The backend has no logic or endpoint to generate a downloadable CSV/Excel file of all submissions.
* **Target Role Metadata:** The UI shows positions and target companies (e.g., "Senior Software Engineer - Google"). The backend database schema only has a flat `target_position` string and does not capture the company/platform cleanly.

### 2.6 Submission Status Enum Mismatches
* **What is in the UI:** Status tabs include `All Status`, `New`, `In Progress`, `Review`, and `Completed`.
* **What is in the backend:** The `SubmissionStatus` enum uses: `new`, `in_progress`, `pending_client_input`, `ai_generated`, `completed`, and `rejected`.
* **Fix needed:** Map `ai_generated` or `pending_client_input` to `Review` on the frontend, or update the database enum to align perfectly with the UI labels (e.g., adding `review` as a valid status state).

---

## 3. Gaps Identified from the PRD Document

### 3.1 PDF, DOCX & LaTeX Document Generation Engine & Version Control
* **What the PRD requires:** 
  * An AI service (`services/openai_service.py`) that feeds client data to OpenAI and returns structured JSON.
  * A document rendering engine that converts the JSON into HTML/CSS, then outputs **PDF** and **Word (DOCX)** documents.
  * Storing completed documents so clients and admins can download them.
  * A `documents` table to track files: `id`, `submission_id`, `type` (pdf/docx), `file_path`, `version`, `created_at`.
* **What is in the backend:** 
  * No document generator service, no template rendering engine, and no database tables or filesystems to store or retrieve generated documents.

### 3.2 AI Generations Tracking & Token Usage Logging
* **What the PRD requires:** 
  * Logging OpenAI API usage costs and tokens.
  * An `ai_generations` database table: `id`, `submission_id`, `model`, `input_tokens`, `output_tokens`, `status`, `created_at`.
* **What is in the backend:** 
  * No database model or service hooks to log OpenAI request tokens.

---

## 4. Gap Analysis Summary Table

| UI / PRD Feature | Backend Model | Backend Router/Controller | Status | Gaps / Action Required |
|---|---|---|---|---|
| **User Roles & Login** | `Admin` | `POST /admin/auth/login` | ✅ Complete | Ready for integration. |
| **Client CV Submission** | `Submission` | `POST /public/submissions` | ✅ Complete | Ready for integration. |
| **Client Chat / Messaging** | `Message` | `POST /public/submissions/{id}/messages` | ✅ Complete | Ready for integration. |
| **File Uploads** | — | `POST /public/upload` | ✅ Complete | Ready for integration. |
| **Dashboard Metrics** | — | — | ❌ Missing | Add `GET /admin/dashboard/stats` |
| **Manage Staff List** | `Admin` | — | ❌ Missing | Add `GET /admin/staff` |
| **Task Management** | — | — | ❌ Missing | Add `Task` model, schemas, and CRUD routes |
| **Prompts Management** | — | — | ❌ Missing | Add `Prompt` model and admin CRUD routes |
| **CV Document Generation** | — | — | ❌ Missing | Add HTML-to-PDF rendering service & files download route |
| **CSV Submission Export** | — | — | ❌ Missing | Add `GET /admin/submissions/export` |
| **Submissions Delete** | `Submission` | — | ❌ Missing | Add `DELETE /admin/submissions/{id}` |

---

## 5. Recommended Technical Implementation Steps

### Phase 1: Implement Missing Database Models (Migrations)
Add the following database tables using SQLAlchemy and run Alembic migrations:
1. `tasks`:
   * `id` (UUID7 primary key)
   * `submission_id` (ForeignKey to submissions)
   * `title` (String)
   * `description` (Text)
   * `assigned_to_id` (ForeignKey to admins, nullable)
   * `priority` (Enum: low, normal, high)
   * `status` (Enum: todo, in_progress, review, done)
   * `deadline` (DateTime, nullable)
2. `prompts`:
   * `id` (UUID7 primary key)
   * `name` (String)
   * `content` (Text)
   * `version` (Integer)
   * `is_active` (Boolean)
3. `documents`:
   * `id` (UUID7 primary key)
   * `submission_id` (ForeignKey to submissions)
   * `file_url` (String/Cloudinary URL)
   * `file_type` (Enum: pdf, docx)
   * `version` (Integer)

### Phase 2: Create Missing API Routers & Controllers
1. **`admin_dashboard_router`**:
   * `GET /api/v1/admin/dashboard/stats` → Aggregate counts of submissions (new, in-progress, completed) and active chats.
2. **`admin_task_router`**:
   * `GET /api/v1/admin/tasks` → Fetch tasks (filtered by assignee, priority, status).
   * `POST /api/v1/admin/tasks` → Create a new task.
   * `PATCH /api/v1/admin/tasks/{task_id}` → Update status, assignee, or priority.
3. **`admin_staff_router`**:
   * `GET /api/v1/admin/staff` → List active staff users for task assignment dropdowns.
4. **`admin_prompt_router`**:
   * `GET /api/v1/admin/prompts` → View available prompt templates.
   * `POST /api/v1/admin/prompts` → Create/version a prompt.
   * `PATCH /api/v1/admin/prompts/{prompt_id}/activate` → Set a prompt as the active master template.
5. **`admin_submission_router` additions**:
   * `DELETE /api/v1/admin/submissions/{submission_id}` → Delete CV request.
   * `GET /api/v1/admin/submissions/export` → Return CSV file stream of submissions.
