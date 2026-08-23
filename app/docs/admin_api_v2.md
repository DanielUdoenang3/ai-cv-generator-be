# AI CV Generator — Admin API v2 Documentation

> **For the Admin Dashboard Frontend Team (React JS)**
> Base URL: `https://ai-cv-generator-be.onrender.com`
> All admin endpoints require a valid `Bearer JWT` token in the `Authorization` header unless stated otherwise.

---

## What's New in v2

This document supersedes the original `admin_api.md`. The following features have been **newly added**:

| Feature | Description |
|---|---|
| 🆕 `reference_id` | Every submission now has a human-readable serial ID (e.g. `SUB-2026-001`) |
| 🆕 `target_company` | Clients can now specify the company they are applying to |
| 🆕 `priority` | Submissions have a priority level: `low`, `normal`, `high` |
| 🆕 `review` status | A new status stage between `in_progress` and `completed` |
| 🆕 `activities` array | Every submission response now includes a full activity timeline (newest first) |
| 🆕 Dashboard Stats | `GET /api/v1/admin/dashboard/stats` |
| 🆕 Recent Submissions | `GET /api/v1/admin/dashboard/recent-submissions` with filters, search, sort, pagination |

---

## Admin Roles (Unchanged)

| Role | Value | Capabilities |
|---|---|---|
| **Super Admin** | `super_admin` | Full access: all submissions, assign staff, change any status |
| **Sub Admin** | `sub_admin` | Limited: only assigned submissions, update status, send messages |

---

## Admin Authentication (Unchanged)

See `admin_api.md` for `POST /api/v1/admin/auth/create-admin`, `POST /api/v1/admin/auth/login`, and `GET /api/v1/admin/auth/profile`. No changes.

---

## Submission Object — What Changed

Previously, a submission object returned these fields: `id`, `status`, `target_position`, `job_description`, `existing_cv_url`, `raw_data`, `created_at`, `updated_at`, `client`, `assigned_to`.

**In v2**, every submission object (from list, get-by-id, assign, status-update endpoints) now includes these additional fields:

```json
{
  "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",

  "reference_id": "SUB-2026-001",
  "target_company": "LinkedIn",
  "priority": "low",

  "status": "review",
  "target_position": "HR Manager",
  "job_description": "...",
  "existing_cv_url": "https://res.cloudinary.com/...",
  "raw_data": { "..." },
  "created_at": "2026-08-22T10:30:00+00:00",
  "updated_at": "2026-08-22T11:45:00+00:00",
  "client": {
    "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Amanda",
    "last_name": "Foster",
    "email": "amanda@email.com",
    "phone": null
  },
  "assigned_to": {
    "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Sarah",
    "last_name": "Johnson",
    "role": "sub_admin"
  },

  "activities": [
    {
      "id": "018f0030-xxxx-7xxx-xxxx-xxxxxxxxxxxx",
      "activity_type": "status_changed",
      "title": "Status Changed to Review",
      "description": "Submission moved to review stage",
      "actor_id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
      "actor_name": "Sarah Johnson",
      "created_at": "2026-08-22T12:00:00+00:00"
    },
    {
      "id": "018f0020-xxxx-7xxx-xxxx-xxxxxxxxxxxx",
      "activity_type": "assigned",
      "title": "Assigned to Sarah Johnson",
      "description": "Submission assigned for review and processing",
      "actor_id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
      "actor_name": "Super Admin",
      "created_at": "2026-08-22T11:00:00+00:00"
    },
    {
      "id": "018f0010-xxxx-7xxx-xxxx-xxxxxxxxxxxx",
      "activity_type": "submission_created",
      "title": "Submission Created",
      "description": "Client submitted CV request through the form",
      "actor_id": null,
      "actor_name": null,
      "created_at": "2026-08-22T10:30:00+00:00"
    }
  ]
}
```

### New Field Reference

| Field | Type | Description |
|---|---|---|
| `reference_id` | string | Human-readable sequential ID. Format: `SUB-YYYY-XXX` (e.g. `SUB-2026-001`). Auto-generated. |
| `target_company` | string \| null | Company the client is applying to. May be `null` if not provided. |
| `priority` | string | Priority level. Default is `"normal"`. Other values: `"low"`, `"high"`. |
| `activities` | array | Chronological audit trail of events. Sorted **newest first**. Empty array `[]` if no events yet. |

---

## Activity Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique UUID7 activity ID |
| `activity_type` | string | One of: `submission_created`, `assigned`, `status_changed` |
| `title` | string | Human-readable event title (e.g. `"Assigned to Sarah Johnson"`) |
| `description` | string \| null | Longer explanation of what happened |
| `actor_id` | string \| null | ID of the admin who performed the action. `null` for system-generated events (like `submission_created`) |
| `actor_name` | string \| null | Full name of the admin who acted. `null` for system events |
| `created_at` | datetime | UTC timestamp of when the event was logged |

### Activity Types

| `activity_type` | When it is logged | `actor_name` present? |
|---|---|---|
| `submission_created` | Automatically on new submission | ❌ No (system event) |
| `assigned` | When a super admin assigns a staff member | ✅ Yes (the assigning admin) |
| `status_changed` | Every time the status is updated | ✅ Yes (the admin who changed it) |

> **Note:** When a submission is assigned and its status is auto-escalated from `new` → `in_progress`, **two** activities are logged: one `assigned` and one `status_changed`.

---

## Submission Status Values (Updated)

A new `review` status has been added. Use this for the status selection buttons in the submission detail UI.

| Value | Description | UI Label |
|---|---|---|
| `new` | Fresh, unassigned submission | "New" |
| `in_progress` | Being actively worked on | "In Progress" |
| `pending_client_input` | Waiting for more info from client | "Pending Client Input" |
| `ai_generated` | AI draft ready, under human review | "AI Generated" |
| `review` | 🆕 CV draft under review stage | "Review" |
| `completed` | Final CV delivered | "Completed" |
| `rejected` | Submission rejected | "Rejected" |

---

## Submission Endpoints (Updated & Paginated Responses)

The main submission management endpoints have been updated. Crucially, the **List All Submissions** endpoint now supports full search, filtering, sorting, and pagination, matching the dashboard table UI.

---

### GET /api/v1/admin/submissions

Returns a paginated, filterable, and searchable list of submissions.

- `super_admin` → Can view all submissions and filter by any staff member.
- `sub_admin` → Automatically restricted to view only submissions assigned to them.

**Requires `Authorization: Bearer <token>` header.**

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Current page number |
| `limit` | integer | `10` | Items per page (max recommended: 50) |
| `search` | string | — | Searches client name, email, target position, target company, and reference ID |
| `status` | string | — | Filter by status (e.g. `new`, `in_progress`, `review`, `completed`) |
| `assigned_to_id` | string | — | **Super Admin only.** Filter by staff ID. Pass `"unassigned"` to show unassigned requests |
| `sort_by` | string | `created_at` | Field to sort by: `created_at`, `updated_at`, `status`, `target_position`, `reference_id`, `priority` |
| `sort_order` | string | `desc` | `"asc"` or `"desc"` |

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Submissions fetched successfully",
  "data": {
    "total": 12,
    "page": 1,
    "limit": 10,
    "pages": 2,
    "submissions": [
      {
        "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
        "reference_id": "SUB-2026-001",
        "target_position": "HR Manager",
        "target_company": "LinkedIn",
        "priority": "low",
        "status": "new",
        "created_at": "2026-08-22T10:30:00+00:00",
        "updated_at": "2026-08-22T11:45:00+00:00",
        "client": {
          "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
          "first_name": "Amanda",
          "last_name": "Foster",
          "email": "amanda@email.com",
          "phone": null
        },
        "assigned_to": null,
        "activities": []
      }
    ]
  }
}
```

---

### GET /api/v1/admin/submissions/{submission_id}
### PATCH /api/v1/admin/submissions/{submission_id}/assign
### PATCH /api/v1/admin/submissions/{submission_id}/status

These endpoints continue to return the full submission detail object (with activities and raw data) shown in the **Submission Object — What Changed** section.

> See `admin_api.md` for original request body and error response details.

---

## 🆕 Client Submission Fields (Updated for v2)

The client-facing submission form now accepts two new **optional** fields. If your form collects this information, pass them in the request body:

**`POST /api/v1/public/submissions`**

```json
{
  "first_name": "Amanda",
  "last_name": "Foster",
  "email": "amanda@email.com",
  "target_position": "HR Manager",
  "target_company": "LinkedIn",
  "priority": "low",
  "raw_data": { "..." }
}
```

| New Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `target_company` | string | ❌ | `null` | The company the client is applying to |
| `priority` | string | ❌ | `"normal"` | Priority level: `"low"`, `"normal"`, `"high"` |

---

## 🆕 Dashboard Endpoints

These are brand new endpoints for powering the admin analytics dashboard.

---

### Dashboard Stats

**`GET /api/v1/admin/dashboard/stats`**

Returns scoped counts for the admin's overview cards.

- `super_admin` → global counts across all submissions
- `sub_admin` → counts scoped to submissions assigned to them

**Requires `Authorization: Bearer <token>` header.**

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Dashboard stats fetched successfully",
  "data": {
    "new_requests": 12,
    "in_progress": 8,
    "completed": 45,
    "active_chats": 5
  }
}
```

| Field | Description |
|---|---|
| `new_requests` | Count of submissions with status `new` |
| `in_progress` | Count of submissions with status `in_progress` |
| `completed` | Count of submissions with status `completed` |
| `active_chats` | Count of conversations with at least one message, on non-terminal submissions |

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid / missing token |

---

### Recent Submissions (Paginated + Filterable)

**`GET /api/v1/admin/dashboard/recent-submissions`**

Returns a paginated, searchable, filterable, and sortable list of submissions. This powers the submission table on the dashboard.

**Requires `Authorization: Bearer <token>` header.**

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Current page number |
| `limit` | integer | `10` | Items per page (max recommended: 50) |
| `search` | string | — | Searches across client first name, last name, email, and target position |
| `status` | string | — | Filter by exact status value (e.g. `in_progress`, `review`) |
| `assigned_to_id` | string | — | **Super admin only.** Filter by assigned staff ID. Pass `"unassigned"` to show unassigned submissions |
| `sort_by` | string | `created_at` | Column to sort by: `created_at`, `updated_at`, `status`, `target_position` |
| `sort_order` | string | `desc` | `"asc"` or `"desc"` |

#### Example Requests

```
# Latest 10 submissions (default)
GET /api/v1/admin/dashboard/recent-submissions

# Search for submissions matching "Amanda"
GET /api/v1/admin/dashboard/recent-submissions?search=Amanda

# Filter by status "review", page 2
GET /api/v1/admin/dashboard/recent-submissions?status=review&page=2

# Unassigned submissions only (super admin)
GET /api/v1/admin/dashboard/recent-submissions?assigned_to_id=unassigned

# Sort by updated_at ascending
GET /api/v1/admin/dashboard/recent-submissions?sort_by=updated_at&sort_order=asc
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Recent submissions fetched successfully",
  "data": {
    "total": 35,
    "page": 1,
    "limit": 10,
    "pages": 4,
    "submissions": [
      {
        "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
        "reference_id": "SUB-2026-001",
        "target_position": "HR Manager",
        "target_company": "LinkedIn",
        "priority": "low",
        "status": "review",
        "created_at": "2026-08-22T10:30:00+00:00",
        "updated_at": "2026-08-22T12:00:00+00:00",
        "client": {
          "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
          "first_name": "Amanda",
          "last_name": "Foster",
          "email": "amanda@email.com",
          "phone": null
        },
        "assigned_to": {
          "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
          "first_name": "Sarah",
          "last_name": "Johnson",
          "role": "sub_admin"
        }
      }
    ]
  }
}
```

> **Note:** The `submissions` array in this endpoint does **not** include `activities` or `raw_data` — it's a lightweight summary for the table view. For full details including the activity timeline, call `GET /api/v1/admin/submissions/{submission_id}`.

#### Pagination Usage

Use `total`, `page`, `limit`, and `pages` to build your pagination UI:

```js
const totalPages = data.pages;
const currentPage = data.page;
const hasNextPage = currentPage < totalPages;
const hasPrevPage = currentPage > 1;
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid / missing token |
| `400 Bad Request` | Invalid sort_by column specified |

---

## Full Endpoint Reference (v2)

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/admin/auth/create-admin` | None | — | Create staff account |
| `POST` | `/api/v1/admin/auth/login` | None | — | Login, get JWT |
| `GET` | `/api/v1/admin/auth/profile` | Bearer JWT | Any | Get own profile |
| `GET` | `/api/v1/admin/submissions` | Bearer JWT | Any | List submissions (role-filtered) |
| `GET` | `/api/v1/admin/submissions/{id}` | Bearer JWT | Any | Get single submission + activity timeline |
| `PATCH` | `/api/v1/admin/submissions/{id}/assign` | Bearer JWT | `super_admin` | Assign to staff |
| `PATCH` | `/api/v1/admin/submissions/{id}/status` | Bearer JWT | Any | Update status |
| `GET` | `/api/v1/admin/submissions/{id}/messages` | Bearer JWT | Any | Get chat messages |
| `POST` | `/api/v1/admin/submissions/{id}/messages` | Bearer JWT | Any | Send message to client |
| `GET` | `/api/v1/admin/dashboard/stats` 🆕 | Bearer JWT | Any | Dashboard overview counts |
| `GET` | `/api/v1/admin/dashboard/recent-submissions` 🆕 | Bearer JWT | Any | Paginated filterable submission table |

---

## Rendering the Activity Timeline (React Example)

```jsx
const activityIcons = {
  submission_created: "📋",
  assigned: "👤",
  status_changed: "🔄",
};

function ActivityTimeline({ activities }) {
  return (
    <ul className="timeline">
      {activities.map((event) => (
        <li key={event.id} className="timeline-item">
          <span className="icon">{activityIcons[event.activity_type]}</span>
          <div className="content">
            <p className="title">{event.title}</p>
            {event.description && (
              <p className="description">{event.description}</p>
            )}
            <p className="meta">
              {event.actor_name ? `by ${event.actor_name} · ` : ""}
              {new Date(event.created_at).toLocaleString()}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
```

> Activities are returned **newest first**, so the first item in the array is always the most recent event. Render them top-to-bottom as-is.

---

## Priority Badge Rendering

```jsx
const priorityColors = {
  low: "bg-gray-100 text-gray-600",
  normal: "bg-blue-100 text-blue-700",
  high: "bg-red-100 text-red-700",
};

function PriorityBadge({ priority }) {
  return (
    <span className={`badge ${priorityColors[priority] || priorityColors.normal}`}>
      {priority} priority
    </span>
  );
}
```

---

## Reference ID Display

`reference_id` is always in the format `SUB-YYYY-XXX`. Display it as a subtitle or chip next to the submission title:

```jsx
<h2>Amanda Foster</h2>
<span className="ref-id">{submission.reference_id}</span>
{/* Renders: SUB-2026-001 */}
```

---

## Status Badge Colors (Recommended Mapping)

| Status | Suggested Color |
|---|---|
| `new` | Blue |
| `in_progress` | Yellow / Amber |
| `pending_client_input` | Orange |
| `ai_generated` | Purple |
| `review` | Indigo |
| `completed` | Green |
| `rejected` | Red |

---

## Dashboard Stats Card Layout

```jsx
function DashboardStats({ stats }) {
  return (
    <div className="stats-grid">
      <StatCard label="New Requests" value={stats.new_requests} color="blue" />
      <StatCard label="In Progress" value={stats.in_progress} color="yellow" />
      <StatCard label="Completed" value={stats.completed} color="green" />
      <StatCard label="Active Chats" value={stats.active_chats} color="purple" />
    </div>
  );
}
```

---

## Common Mistakes to Avoid

| Mistake | Fix |
|---|---|
| Expecting `activities` in the dashboard recent-submissions list | `activities` is only in the single submission detail endpoint |
| Rendering activities oldest-first | The API returns newest-first — render top-to-bottom as-is |
| Using the old status list without `review` | Update your status dropdowns and filters to include `"review"` |
| Assuming `target_company` is always set | It can be `null` — guard before rendering |
| Hardcoding `priority` as a boolean | It's a string: `"low"`, `"normal"`, or `"high"` |

---

## 🆕 Admin Profile Update Endpoint

### PUT /api/v1/admin/auth/profile

Allows the authenticated admin to update their own profile details.

**Requires `Authorization: Bearer <token>` header.**

#### Request Body
```json
{
  "first_name": "NewName",
  "last_name": "NewLast",
  "email": "newprofile@example.com",
  "phone": "+2348000000",
  "gender": "male"
}
```

*Note: All fields are optional. Role cannot be changed.*

#### Success Response — `200 OK`
```json
{
  "status": "success",
  "message": "Profile updated successfully",
  "data": {
    "id": "...",
    "first_name": "NewName",
    "last_name": "NewLast",
    "email": "newprofile@example.com",
    "role": "sub_admin",
    "gender": "male",
    "phone": "+2348000000",
    "is_active": true,
    "access_token": "🆕_jwt_token_here_if_email_changed"
  }
}
```
*Note: If the email changes, the response includes a new `access_token` since the JWT contains the email. The frontend must replace the active session token with this new one.*

---

## 🆕 Staff Management Endpoints

---

### GET /api/v1/admin/staff

Returns a list of all staff members along with system-wide workload analytics.

**Requires `Authorization: Bearer <token>` header.**

#### Success Response — `200 OK`
```json
{
  "status": "success",
  "message": "Staff list fetched successfully",
  "data": {
    "stats": {
      "total_staff": 3,
      "active_members": 3,
      "avg_workload": 2.7
    },
    "staff": [
      {
        "id": "...",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "email": "sarah@company.com",
        "phone": "+12345678",
        "gender": "female",
        "role": "sub_admin",
        "is_active": true,
        "created_at": "2023-03-15T08:00:00.000Z",
        "active_count": 4,
        "completed_count": 32
      }
    ]
  }
}
```

---

### POST /api/v1/admin/staff

Creates a new staff/admin member.

**Requires `Authorization: Bearer <token>` (Super Admin only).**

#### Request Body
```json
{
  "first_name": "Sarah",
  "last_name": "Johnson",
  "email": "sarah@company.com",
  "password": "Password123!",
  "role": "sub_admin",
  "phone": "+12345678",
  "gender": "female"
}
```

#### Success Response — `200 OK`
```json
{
  "status": "success",
  "message": "Staff member created successfully",
  "data": {
    "id": "...",
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah@company.com",
    "role": "sub_admin",
    "gender": "female",
    "phone": "+12345678",
    "is_active": true
  }
}
```

---

### DELETE /api/v1/admin/staff/{staff_id}

Deletes a staff/admin member. 

**Requires `Authorization: Bearer <token>` (Super Admin only).**

*Self-deletion is blocked. When a staff member is deleted, any submissions assigned to them are automatically unassigned (`assigned_to_id` set to `None`), and an audit log event is added to their activity history.*

#### Success Response — `200 OK`
```json
{
  "status": "success",
  "message": "Staff member deleted successfully"
}
```

