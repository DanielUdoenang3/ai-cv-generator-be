# AI CV Generator — AI Generation, Document Rendering & Kanban Tasks Frontend Integration Guide

> **Target Audience:** React JS Frontend Engineers (Admin Dashboard & Client Portal)  
> **Base URL:** `https://ai-cv-generator-be.onrender.com`  
> **API Version:** `v1`  
> **Response Envelope:** All standard responses return JSON wrapped in `{ status, message, data }`. Binary file download endpoints stream raw byte streams (`application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

---

## Table of Contents

1. [Architecture & Authentication Summary](#1-architecture--authentication-summary)
2. [Module 1: AI Prompt Management (Admin Dashboard)](#2-module-1-ai-prompt-management-admin-dashboard)
3. [Module 2: AI CV Generation Engine (Admin Dashboard)](#3-module-2-ai-cv-generation-engine-admin-dashboard)
4. [Module 3: Document Rendering & File Downloads (Admin & Client)](#4-module-3-document-rendering--file-downloads-admin--client)
5. [Module 4: Kanban Task Management Board (Admin Dashboard)](#5-module-4-kanban-task-management-board-admin-dashboard)
6. [React JS Code Patterns & Quick Reference](#6-react-js-code-patterns--quick-reference)

---

## 1. Architecture & Authentication Summary

The system is divided into two distinct interaction domains:

| Domain | Intended Users | Auth Mechanism | Base URL Prefix |
|---|---|---|---|
| **Admin API** | Super Admins & Sub Admins | `Authorization: Bearer <JWT_TOKEN>` | `/api/v1/admin` |
| **Client API** | End-user Clients tracking requests | `X-Client-Access-Token: <ACCESS_TOKEN>` | `/api/v1/public` |

### Response Envelope Pattern

Every JSON response from the API follows this structure:

```typescript
// Standard JSON Envelope
interface ApiResponse<T> {
  status: "success" | "error";
  message: string;
  data: T;
}
```

#### Example Success Response (200 / 201)
```json
{
  "status": "success",
  "message": "Prompts retrieved successfully",
  "data": [ ... ]
}
```

#### Example Error Response (400 / 401 / 403 / 404 / 422)
```json
{
  "status": "error",
  "message": "You are not assigned to this submission",
  "data": null
}
```

---

## 2. Module 1: AI Prompt Management (Admin Dashboard)

### UI Context
Use these endpoints on the **Admin Settings → System Prompts** page (`/admin/prompts`).  
This view allows Admins to manage master prompt templates used by the AI when generating CVs. It supports role-based categories (e.g., `tech`, `executive`, `creative`, `general`) and activation toggles.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SYSTEM PROMPT MANAGEMENT                                  [+ Create Prompt] │
├──────────────────────────┬─────────────────────────┬────────────────────────┤
│ Total Prompts: 8         │ Active Prompts: 3       │ Total AI Runs: 142     │
├──────────────────────────┴─────────────────────────┴────────────────────────┤
│ Search: [ Filter by title/category... ]  Category: [ All Categories ▾ ]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ TITLE                 │ CATEGORY  │ TARGET ROLE      │ USAGE  │ STATUS     │
├───────────────────────┼───────────┼──────────────────┼────────┼────────────┤
│ Tech Engineer Master  │ tech      │ Software Eng...  │ 84     │ [Active 🟢]│
│ Executive Leadership  │ executive │ VP, Director...  │ 32     │ [Active 🟢]│
│ General Modern CV     │ general   │ Any              │ 26     │ [Active 🟢]│
└───────────────────────┴───────────┴──────────────────┴────────┴────────────┘
```

---

### Endpoints Breakdown

#### 1. Get Prompt Dashboard Statistics
- **Method / Path:** `GET /api/v1/admin/prompts/stats`
- **Auth:** `Bearer JWT` (Admin)
- **Use Case:** Renders top summary cards on the prompt settings page.

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Prompt stats fetched successfully",
  "data": {
    "total_prompts": 8,
    "active_prompts": 3,
    "total_usage": 142
  }
}
```

---

#### 2. List & Filter Prompts
- **Method / Path:** `GET /api/v1/admin/prompts`
- **Auth:** `Bearer JWT` (Admin)
- **Query Params:**
  - `is_active` (boolean, optional): `true` or `false`
  - `category` (string, optional): e.g. `tech`, `executive`, `marketing_sales`, `general`
  - `search` (string, optional): Search keyword against prompt title, target position, or description.

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Prompts retrieved successfully",
  "data": [
    {
      "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
      "title": "Tech Engineering Master Prompt",
      "target_position": "Software Engineer, DevOps, Backend Developer",
      "category": "tech",
      "prompt_text": "You are an expert technical CV resume writer...",
      "description": "Optimized for software engineers and IT professionals",
      "is_active": true,
      "is_default": true,
      "usage_count": 84,
      "created_at": "2026-08-26T10:00:00+00:00",
      "updated_at": "2026-08-27T04:00:00+00:00"
    }
  ]
}
```

---

#### 3. Create System Prompt
- **Method / Path:** `POST /api/v1/admin/prompts`
- **Auth:** `Bearer JWT` (Super Admin or Sub Admin)
- **Request Body:**
```json
{
  "title": "Executive Leadership Master Prompt",
  "target_position": "CTO, VP of Engineering, Director",
  "category": "executive",
  "prompt_text": "You are an executive career strategist crafting C-level resumes...",
  "description": "Tailored for high-level executive positions",
  "is_active": true,
  "is_default": false
}
```

**Response `201 Created`:**
```json
{
  "status": "success",
  "message": "Prompt created successfully",
  "data": {
    "id": "018f4a30-9999-7ccc-8888-1c2d3e4f5a6b",
    "title": "Executive Leadership Master Prompt",
    "target_position": "CTO, VP of Engineering, Director",
    "category": "executive",
    "prompt_text": "You are an executive career strategist crafting C-level resumes...",
    "description": "Tailored for high-level executive positions",
    "is_active": true,
    "is_default": false,
    "usage_count": 0,
    "created_at": "2026-08-27T06:00:00+00:00",
    "updated_at": "2026-08-27T06:00:00+00:00"
  }
}
```

---

#### 4. Update System Prompt
- **Method / Path:** `PUT /api/v1/admin/prompts/{prompt_id}`
- **Auth:** `Bearer JWT` (Admin)
- **Request Body:** (All fields optional, updates specified values)
```json
{
  "title": "Updated Prompt Title",
  "prompt_text": "Updated system instructions...",
  "category": "tech"
}
```

---

#### 5. Activate / Deactivate Prompt Toggles
- **Activate Endpoint:** `PATCH /api/v1/admin/prompts/{prompt_id}/activate`
- **Deactivate Endpoint:** `PATCH /api/v1/admin/prompts/{prompt_id}/deactivate`
- **Auth:** `Bearer JWT` (Admin)
- **Use Case:** Direct button click on UI switch toggle without sending full payload.

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Prompt activated successfully",
  "data": {
    "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "is_active": true
  }
}
```

---

#### 6. Delete System Prompt
- **Method / Path:** `DELETE /api/v1/admin/prompts/{prompt_id}`
- **Auth:** `Bearer JWT` (Admin)

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Prompt deleted successfully"
}
```

---

## 3. Module 2: AI CV Generation Engine (Admin Dashboard)

### UI Context
Used in the **Admin Submission Workspace** (`/admin/submissions/:submission_id`).  
When an Admin opens a submission, they can click **"Generate AI CV"**. The system inspects the client's requested position (e.g. *"Software Engineer"*), dynamically picks the smartest active prompt, runs the LLM, and produces a structured JSON CV object.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SUBMISSION: SUB-2026-001  —  Jane Render (Senior Backend Engineer)         │
├─────────────────────────────────────────────────────────────────────────────┤
│  AI Model: [ OpenAI gpt-4o ▾ ]  Provider: [ OpenAI ▾ ]                     │
│  Custom Instructions: [ Focus heavily on AWS and high-throughput APIs     ] │
│                                                                             │
│  [ ⚡ Trigger AI Generation ]                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ GENERATION HISTORY                                                          │
│  #1  gpt-4o   Tokens: 1,420 (in: 850 / out: 570)  Cost: $0.012  [Success 🟢] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Endpoints Breakdown

#### 1. Trigger AI Generation
- **Method / Path:** `POST /api/v1/admin/submissions/{submission_id}/generate`
- **Auth:** `Bearer JWT` (Super Admin, or Sub Admin assigned to the submission)
- **Request Body:**
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "prompt_id": null,
  "custom_instructions": "Highlight microservices architecture and Python FastAPI achievements prominently."
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `provider` | string | ❌ | `"openai"` or `"gemini"`. Default: `"openai"` |
| `model` | string | ❌ | e.g., `"gpt-4o"`, `"gpt-4o-mini"`, `"gemini-1.5-pro"`. Default: `"gpt-4o"` |
| `prompt_id` | string \| null | ❌ | Pass explicit prompt ID to override smart auto-selection. Pass `null` for auto-selection. |
| `custom_instructions` | string \| null | ❌ | Additional instructions injected into generation run. |

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "AI CV generated successfully",
  "data": {
    "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
    "model_used": "gpt-4o",
    "prompt_used_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "prompt_title": "Tech Engineering Master Prompt",
    "tokens": {
      "input_tokens": 920,
      "output_tokens": 640,
      "total_tokens": 1560
    },
    "cost": 0.0124,
    "structured_cv": {
      "personal_info": {
        "full_name": "Jane Render",
        "email": "jane.render@example.com",
        "phone": "+1-555-0199",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/janerender",
        "portfolio": "janerender.dev",
        "target_role": "Senior Backend Engineer"
      },
      "professional_summary": "Seasoned Senior Backend Engineer with 6+ years of experience specializing in high-throughput distributed systems...",
      "work_experience": [
        {
          "company": "Acme Tech Corp",
          "job_title": "Senior Backend Developer",
          "location": "San Francisco, CA",
          "start_date": "2021-03",
          "end_date": None,
          "is_current": true,
          "bullet_points": [
            "Architected microservices processing over 10M daily requests using FastAPI and PostgreSQL.",
            "Reduced API latency by 45% through Redis caching strategies."
          ]
        }
      ],
      "education": [
        {
          "institution": "University of California, Berkeley",
          "degree": "B.S. Computer Science",
          "location": "Berkeley, CA",
          "graduation_year": "2020",
          "honors": "Magna Cum Laude"
        }
      ],
      "skills": {
        "Languages": ["Python", "Go", "SQL"],
        "Frameworks & Tools": ["FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Redis"],
        "Cloud": ["AWS (ECS, Lambda, S3)", "GCP"]
      },
      "projects": [
        {
          "title": "Real-time Event Streamer",
          "description": "Open-source asynchronous message broker interface built in Python.",
          "link": "github.com/janerender/streamer",
          "tech_stack": ["Python", "AsyncIO", "WebSockets"]
        }
      ],
      "certifications": [
        "AWS Certified Solutions Architect – Associate"
      ]
    }
  }
}
```

---

#### 2. Get AI Generation History
- **Method / Path:** `GET /api/v1/admin/submissions/{submission_id}/generations`
- **Auth:** `Bearer JWT` (Admin)
- **Use Case:** Renders history list of previous AI generation runs for auditing token counts & costs.

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Generations retrieved successfully",
  "data": [
    {
      "id": "018f4a50-aaaa-7bbb-cccc-111122223333",
      "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
      "model": "gpt-4o",
      "input_tokens": 920,
      "output_tokens": 640,
      "cost": 0.0124,
      "status": "success",
      "error_message": null,
      "created_at": "2026-08-27T06:10:00+00:00"
    }
  ]
}
```

---

#### 3. Real-Time WebSocket Notification
When AI generation completes, the backend broadcasts a WebSocket event on channel `/api/v1/admin/submissions/{submission_id}/ws`:

```json
{
  "event": "cv_generated",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
    "model": "gpt-4o",
    "generated_by": "Sarah Johnson"
  }
}
```

---

## 4. Module 3: Document Rendering & File Downloads (Admin & Client)

### UI Context

#### Admin Panel (`/admin/submissions/:submission_id`)
After generating an AI CV, the Admin can click **"Render Documents"**.  
They can choose output formats (`PDF`, `DOCX`, or both). The backend compiles the structured JSON into HTML using a WeasyPrint paged CSS template, programmatically builds a Word document with `python-docx`, uploads both to Cloudinary, and returns download records.

#### Client Public Portal (`/status/:submission_id`)
When the client views their submission status page, ready-to-download documents are automatically returned in the submission payload, or can be fetched/downloaded directly.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXPORTED DOCUMENTS                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  📄 Jane_Render_CV_v1.pdf   (Version 1 · PDF)    [ ⬇️ Download PDF ]     │
│  📝 Jane_Render_CV_v1.docx  (Version 1 · DOCX)   [ ⬇️ Download DOCX ]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Admin Document Endpoints

#### 1. Render Documents (Admin Triggered)
- **Method / Path:** `POST /api/v1/admin/submissions/{submission_id}/documents/render`
- **Auth:** `Bearer JWT` (Super Admin, or Sub Admin assigned to submission)
- **Request Body:**
```json
{
  "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
  "formats": ["pdf", "docx"]
}
```

**Response `201 Created`:**
```json
{
  "status": "success",
  "message": "CV rendered successfully in 2 format(s)",
  "data": [
    {
      "id": "018f4b10-1111-7222-3333-444455556666",
      "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
      "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
      "file_name": "Jane_Render_CV_v1.pdf",
      "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/documents/018f4a2b/pdf_v1.pdf",
      "public_id": "ai_cv_generator/documents/018f4a2b/pdf_v1",
      "file_type": "pdf",
      "version": 1,
      "created_at": "2026-08-27T06:15:00+00:00"
    },
    {
      "id": "018f4b11-1111-7222-3333-444455556666",
      "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
      "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
      "file_name": "Jane_Render_CV_v1.docx",
      "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/documents/018f4a2b/docx_v1.docx",
      "public_id": "ai_cv_generator/documents/018f4a2b/docx_v1",
      "file_type": "docx",
      "version": 1,
      "created_at": "2026-08-27T06:15:01+00:00"
    }
  ]
}
```

---

#### 2. List Submission Documents (Admin)
- **Method / Path:** `GET /api/v1/admin/submissions/{submission_id}/documents`
- **Auth:** `Bearer JWT` (Admin)

**Response `200 OK`:** Returns array of document objects matching the structure above.

---

#### 3. Download Document Binary File (Admin)
- **Method / Path:** `GET /api/v1/admin/submissions/{submission_id}/documents/{document_id}/download`
- **Auth:** `Bearer JWT` (Admin)
- **Response:** Raw binary file payload (`Content-Type: application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`) with header `Content-Disposition: attachment; filename="Jane_Render_CV_v1.pdf"`.

---

### Client Document Endpoints

#### 1. Embedded Documents in Submission Status
- **Method / Path:** `GET /api/v1/public/submissions/{submission_id}`
- **Auth Header:** `X-Client-Access-Token: <access_token>`

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Submission fetched successfully",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "status": "completed",
    "target_position": "Senior Backend Engineer",
    "created_at": "2026-08-27T05:00:00+00:00",
    "updated_at": "2026-08-27T06:15:00+00:00",
    "client": {
      "first_name": "Jane",
      "last_name": "Render",
      "email": "jane.render@example.com"
    },
    "assigned_to": {
      "first_name": "Sarah",
      "last_name": "Johnson"
    },
    "documents": [
      {
        "id": "018f4b10-1111-7222-3333-444455556666",
        "file_name": "Jane_Render_CV_v1.pdf",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/documents/018f4a2b/pdf_v1.pdf",
        "file_type": "pdf",
        "version": 1,
        "created_at": "2026-08-27T06:15:00+00:00"
      },
      {
        "id": "018f4b11-1111-7222-3333-444455556666",
        "file_name": "Jane_Render_CV_v1.docx",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/documents/018f4a2b/docx_v1.docx",
        "file_type": "docx",
        "version": 1,
        "created_at": "2026-08-27T06:15:01+00:00"
      }
    ]
  }
}
```

---

#### 2. Dedicated Client Document List Endpoint
- **Method / Path:** `GET /api/v1/public/submissions/{submission_id}/documents`
- **Auth Header:** `X-Client-Access-Token: <access_token>`

---

#### 3. Client Download Document Binary File
- **Method / Path:** `GET /api/v1/public/submissions/{submission_id}/documents/{document_id}/download`
- **Auth Header:** `X-Client-Access-Token: <access_token>`
- **Response:** Direct binary stream for browser download.

---

## 5. Module 4: Kanban Task Management Board (Admin Dashboard)

### UI Context
Used for the **Admin Dashboard → Kanban Tasks Board** (`/admin/tasks`).  
Allows staff and super admins to create, track, drag-and-drop, and complete operational tasks associated with CV fulfillment.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KANBAN TASK BOARD                                            [+ New Task]   │
├───────────────┬────────────────┬─────────────────┬──────────────────────────┤
│ Total: 24     │ To Do: 8       │ In Progress: 10 │ Done: 6  (Overdue: 2)    │
├───────────────┴────────────────┴─────────────────┴──────────────────────────┤
│                                                                             │
│ [ TO DO (8) ]       [ IN PROGRESS (10) ]   [ REVIEW (3) ]    [ DONE (6) ]   │
│ ┌─────────────────┐ ┌──────────────────┐ ┌───────────────┐ ┌──────────────┐ │
│ │ Revise Summary  │ │ Format Work Exp  │ │ Final Proof   │ │ Client Email │ │
│ │ High · SUB-001  │ │ Normal · SUB-002 │ │ High          │ │ Low          │ │
│ └─────────────────┘ └──────────────────┘ └───────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Task Data Object Definition

```typescript
interface KanbanTask {
  id: string;
  submission_id?: string | null;
  assigned_to_id?: string | null;
  created_by_id: string;
  title: string;
  description?: string | null;
  status: "todo" | "in_progress" | "review" | "done";
  priority: "low" | "normal" | "high" | "urgent";
  due_date?: string | null; // UTC ISO String
  is_overdue: boolean;
  created_at: string;
  updated_at: string;

  // Embedded relational descriptors
  created_by?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
  } | null;

  assigned_to?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
  } | null;

  submission?: {
    id: string;
    reference_id: string;
    target_position: string;
    client_name?: string;
  } | null;
}
```

---

### Endpoints Breakdown

#### 1. Get Kanban Board Metrics Summary
- **Method / Path:** `GET /api/v1/admin/tasks/metrics`
- **Auth:** `Bearer JWT` (Admin)
- **Use Case:** Powers top stats widgets on the Kanban board view.

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Task metrics fetched successfully",
  "data": {
    "total_tasks": 24,
    "overdue_tasks": 2,
    "by_status": {
      "todo": 8,
      "in_progress": 10,
      "review": 3,
      "done": 3
    },
    "by_priority": {
      "low": 4,
      "normal": 12,
      "high": 6,
      "urgent": 2
    }
  }
}
```

---

#### 2. List Kanban Tasks
- **Method / Path:** `GET /api/v1/admin/tasks`
- **Auth:** `Bearer JWT` (Admin)
- **Query Params:**
  - `status` (string, optional): `todo`, `in_progress`, `review`, `done`
  - `priority` (string, optional): `low`, `normal`, `high`, `urgent`
  - `submission_id` (string, optional): Filter tasks for a single submission
  - `assigned_to_id` (string, optional): Filter by staff ID (`"unassigned"` to filter unassigned)
  - `search` (string, optional): Search keyword against task title and description

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Tasks retrieved successfully",
  "data": [
    {
      "id": "018f4c00-aaaa-7bbb-cccc-111122223333",
      "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
      "assigned_to_id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
      "created_by_id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
      "title": "Review executive summary tone for Jane Render",
      "description": "Ensure executive metrics align with target VP role.",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2026-08-28T17:00:00+00:00",
      "is_overdue": false,
      "created_at": "2026-08-27T05:00:00+00:00",
      "updated_at": "2026-08-27T06:00:00+00:00",
      "created_by": {
        "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
        "first_name": "Super",
        "last_name": "Admin",
        "email": "admin@example.com"
      },
      "assigned_to": {
        "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "email": "sarah@example.com"
      },
      "submission": {
        "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
        "reference_id": "SUB-2026-001",
        "target_position": "Senior Backend Engineer",
        "client_name": "Jane Render"
      }
    }
  ]
}
```

---

#### 3. Create Task
- **Method / Path:** `POST /api/v1/admin/tasks`
- **Auth:** `Bearer JWT` (Admin)
- **Request Body:**
```json
{
  "title": "Verify GitHub portfolio links",
  "description": "Double check all links in the project section resolve.",
  "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
  "assigned_to_id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
  "status": "todo",
  "priority": "normal",
  "due_date": "2026-08-29T12:00:00Z"
}
```

---

#### 4. Update Task Status (Drag and Drop Handler)
- **Method / Path:** `PATCH /api/v1/admin/tasks/{task_id}/status`
- **Auth:** `Bearer JWT` (Admin)
- **Use Case:** Triggered when a user drags a task card from one column to another on the Kanban board.
- **Request Body:**
```json
{
  "status": "review"
}
```

**Response `200 OK`:**
```json
{
  "status": "success",
  "message": "Task status updated to review",
  "data": {
    "id": "018f4c00-aaaa-7bbb-cccc-111122223333",
    "status": "review",
    "updated_at": "2026-08-27T06:20:00+00:00"
  }
}
```

---

#### 5. Full Update Task
- **Method / Path:** `PUT /api/v1/admin/tasks/{task_id}`
- **Auth:** `Bearer JWT` (Admin)
- **Request Body:** (Modifies title, priority, due date, assigned staff, etc.)

---

#### 6. Delete Task
- **Method / Path:** `DELETE /api/v1/admin/tasks/{task_id}`
- **Auth:** `Bearer JWT` (Admin)

---

## 6. React JS Code Patterns & Quick Reference

### 1. Handling File Downloads (Axios + Blob Anchor)
When calling binary download endpoints, specify `responseType: "blob"`.

```jsx
import axios from "axios";

async function downloadDocument(submissionId, documentId, fileName, userRole = "client", token) {
  try {
    const isClient = userRole === "client";
    const url = isClient
      ? `/api/v1/public/submissions/${submissionId}/documents/${documentId}/download`
      : `/api/v1/admin/submissions/${submissionId}/documents/${documentId}/download`;

    const headers = isClient
      ? { "X-Client-Access-Token": token }
      : { Authorization: `Bearer ${token}` };

    const response = await axios.get(url, {
      headers,
      responseType: "blob", // CRITICAL for binary streaming
    });

    // Create an in-memory blob URL and trigger download
    const blob = new Blob([response.data], {
      type: response.headers["content-type"],
    });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", fileName || "CV_Document");
    document.body.appendChild(link);
    link.click();

    // Clean up
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("Failed to download document:", error);
  }
}
```

---

### 2. React Drag-and-Drop Handler for Kanban Board
Example using state optimistic update for instant UI response during drag-and-drop:

```jsx
import { useState } from "react";
import axios from "axios";

function useKanbanBoard(initialTasks, jwtToken) {
  const [tasks, setTasks] = useState(initialTasks);

  const handleDragEnd = async (taskId, newStatus) => {
    // 1. Optimistic UI update
    setTasks((prevTasks) =>
      prevTasks.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
    );

    // 2. Persist to API
    try {
      await axios.patch(
        `/api/v1/admin/tasks/${taskId}/status`,
        { status: newStatus },
        { headers: { Authorization: `Bearer ${jwtToken}` } }
      );
    } catch (err) {
      console.error("Failed to save task move — reverting UI state", err);
      // Revert on error
      setTasks(initialTasks);
    }
  };

  return { tasks, handleDragEnd };
}
```

---

### 3. Quick Security & Integration Checklist

- [ ] **Client Token Persistence:** Always save `access_token` and `submission_id` to `localStorage` immediately after `POST /api/v1/public/submissions`.
- [ ] **Header Alias:** Send `X-Client-Access-Token` with the exact capitalization for client requests.
- [ ] **Download Response Type:** Ensure Axios/Fetch uses `responseType: 'blob'` when downloading PDF/DOCX binary files.
- [ ] **Status Mapping Color Scheme:**
  - `todo` / `new`: Blue badge (`#3B82F6`)
  - `in_progress`: Amber badge (`#F59E0B`)
  - `review` / `ai_generated`: Purple badge (`#8B5CF6`)
  - `done` / `completed`: Green badge (`#10B981`)
  - `urgent` / `rejected`: Red badge (`#EF4444`)
