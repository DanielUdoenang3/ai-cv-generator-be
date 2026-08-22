# AI CV Generator — Admin API Documentation

> **For the Admin Dashboard Frontend Team (React JS)**
> Base URL: `https://ai-cv-generator-be.onrender.com`
> All admin endpoints require a valid `Bearer JWT` token in the `Authorization` header.

---

## Overview

The Admin API is used exclusively by internal staff. There are **two admin roles** that control what each person can see and do:

| Role | Value | Capabilities |
|---|---|---|
| **Super Admin** | `super_admin` | Full access: see all submissions, assign to any staff, change any status |
| **Sub Admin** | `sub_admin` | Limited access: see only assigned submissions, update status on assigned submissions, send messages on assigned submissions |

---

## Admin Authentication

---

### 1. Create Admin Account

**`POST /api/v1/admin/auth/create-admin`**

Creates a new admin/staff account. Currently open (no auth guard active in code — the commented-out guard means any request can create an admin, so protect this in production from the frontend by only calling it from a protected admin dashboard page).

**No auth required (currently).**

#### Request Body (JSON)

```json
{
  "first_name": "Sarah",
  "last_name": "Ade",
  "email": "sarah.ade@company.com",
  "password": "StrongPass123!",
  "role": "sub_admin",
  "phone": "+2348098765432",
  "gender": "female"
}
```

#### Field Reference

| Field | Type | Required | Valid Values |
|---|---|---|---|
| `first_name` | string | ✅ | |
| `last_name` | string | ✅ | |
| `email` | string (email) | ✅ | Must be unique |
| `password` | string | ✅ | Plain text — hashed on the server |
| `role` | string | ❌ | `"super_admin"` or `"sub_admin"` (default: `"sub_admin"`) |
| `phone` | string | ❌ | |
| `gender` | string | ❌ | `"male"`, `"female"`, `"other"` |

#### Success Response — `201 Created`

```json
{
  "status": "success",
  "message": "Admin created successfully",
  "data": {
    "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Sarah",
    "last_name": "Ade",
    "email": "sarah.ade@company.com",
    "role": "sub_admin",
    "gender": "female",
    "phone": "+2348098765432",
    "is_active": true
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | Email already exists, or password hashing failed |
| `422 Unprocessable Entity` | Invalid email format or missing required fields |

---

### 2. Admin Login

**`POST /api/v1/admin/auth/login`**

Authenticates a staff member and returns a JWT access token. Store this token — it must be sent in every subsequent admin API request.

**No auth required.**

#### Request Body (JSON)

```json
{
  "email": "sarah.ade@company.com",
  "password": "StrongPass123!"
}
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Admin logged in successfully",
  "data": {
    "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Sarah",
    "last_name": "Ade",
    "email": "sarah.ade@company.com",
    "role": "sub_admin",
    "gender": "female",
    "phone": "+2348098765432",
    "is_active": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6..."
  }
}
```

> **Save the `access_token`** — send it as `Authorization: Bearer <token>` in every admin request.

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Wrong email (user not found) |
| `401 Unauthorized` | Wrong password |
| `403 Forbidden` | Account is deactivated (`is_active: false`) |

---

### 3. Get Admin Profile

**`GET /api/v1/admin/auth/profile`**

Returns the currently logged-in admin's full profile. Useful for displaying the user's name, role badge, and last login time in the dashboard header.

**Requires `Authorization: Bearer <token>` header.**

#### Request Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Admin profile fetched successfully",
  "data": {
    "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Sarah",
    "last_name": "Ade",
    "email": "sarah.ade@company.com",
    "role": "sub_admin",
    "gender": "female",
    "phone": "+2348098765432",
    "is_active": true,
    "last_login": "2026-08-22T10:00:00.000000+00:00",
    "created_at": "2026-08-20T08:00:00.000000+00:00",
    "updated_at": "2026-08-22T10:00:00.000000+00:00"
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | No token / invalid token / expired token / account deactivated |

---

## Submission Management

All submission endpoints sit under `/api/v1/admin/submissions/` and require a valid Bearer token.

---

### 4. List All Submissions

**`GET /api/v1/admin/submissions`**

Returns a list of submissions. **The result set depends on the caller's role:**

- `super_admin` → gets **ALL** submissions in the system, newest first
- `sub_admin` → gets **ONLY** submissions that have been assigned to their account

**Requires `Authorization: Bearer <token>` header.**

#### Request Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Submissions fetched successfully",
  "data": {
    "total": 2,
    "submissions": [
      {
        "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
        "status": "in_progress",
        "target_position": "Senior Backend Engineer",
        "job_description": "We are looking for a backend engineer...",
        "existing_cv_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/resumes/old_cv.pdf",
        "raw_data": {
          "education": [...],
          "experience": [...],
          "skills": ["Python", "FastAPI", "PostgreSQL"],
          "certifications": [...],
          "custom_notes": "I prefer remote-first teams."
        },
        "created_at": "2026-08-22 10:30:00.000000+00:00",
        "updated_at": "2026-08-22 11:45:00.000000+00:00",
        "client": {
          "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
          "first_name": "John",
          "last_name": "Doe",
          "email": "john.doe@example.com",
          "phone": "+2348012345678"
        },
        "assigned_to": {
          "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
          "first_name": "Sarah",
          "last_name": "Ade",
          "role": "sub_admin"
        }
      }
    ]
  }
}
```

> `assigned_to` is `null` if no staff has been assigned yet.
> `client.phone` may be `null` if the client did not provide it.

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid / expired / missing token |

---

### 5. Get Single Submission Details

**`GET /api/v1/admin/submissions/{submission_id}`**

Fetches full details of one specific submission, including the client's raw CV data.

- `super_admin` → can view any submission
- `sub_admin` → can only view submissions assigned to them (returns 403 otherwise)

**Requires `Authorization: Bearer <token>` header.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The submission to retrieve |

#### Success Response — `200 OK`

Same shape as a single item in the list endpoint:

```json
{
  "status": "success",
  "message": "Submission fetched successfully",
  "data": {
    "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "status": "in_progress",
    "target_position": "Senior Backend Engineer",
    "job_description": "We are looking for a backend engineer...",
    "existing_cv_url": "https://res.cloudinary.com/.../old_cv.pdf",
    "raw_data": {
      "education": [
        {
          "institution": "University of Lagos",
          "degree": "B.Sc Computer Science",
          "field_of_study": "Computer Science",
          "start_date": "2015",
          "end_date": "2019",
          "description": "Graduated with Second Class Upper"
        }
      ],
      "experience": [
        {
          "company": "Flutterwave",
          "role": "Backend Developer",
          "start_date": "2020-01",
          "end_date": "2023-06",
          "description": "Built payment APIs used by 500k+ merchants"
        }
      ],
      "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
      "certifications": [
        {
          "name": "AWS Certified Solutions Architect",
          "issuing_organization": "Amazon Web Services",
          "issue_date": "2022-03",
          "expiration_date": "2025-03"
        }
      ],
      "custom_notes": "I prefer remote-first teams."
    },
    "created_at": "2026-08-22 10:30:00.000000+00:00",
    "updated_at": "2026-08-22 11:45:00.000000+00:00",
    "client": {
      "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "phone": "+2348012345678"
    },
    "assigned_to": {
      "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
      "first_name": "Sarah",
      "last_name": "Ade",
      "role": "sub_admin"
    }
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid / missing token |
| `403 Forbidden` | Sub-admin trying to view a submission not assigned to them |
| `404 Not Found` | Submission with this ID does not exist |

---

### 6. Assign Submission to Staff

**`PATCH /api/v1/admin/submissions/{submission_id}/assign`**

Assigns (or reassigns) a submission to a specific staff member. **Only `super_admin` can call this.** Sub-admins will get a 401 error.

**Side effect**: If the submission status is `new` at the time of assignment, it is automatically promoted to `in_progress`.

**Requires `Authorization: Bearer <token>` — caller must be `super_admin`.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The submission to assign |

#### Request Body (JSON)

```json
{
  "assigned_to_id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `assigned_to_id` | string (UUID) | ✅ | The `id` of an active admin/staff account |

#### Success Response — `200 OK`

Returns the full updated submission object (same shape as Get Single Submission):

```json
{
  "status": "success",
  "message": "Submission successfully assigned to Sarah Ade",
  "data": {
    "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "status": "in_progress",
    "target_position": "Senior Backend Engineer",
    "job_description": "...",
    "existing_cv_url": "...",
    "raw_data": { ... },
    "created_at": "2026-08-22 10:30:00.000000+00:00",
    "updated_at": "2026-08-22 12:00:00.000000+00:00",
    "client": {
      "id": "...",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "phone": "+2348012345678"
    },
    "assigned_to": {
      "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
      "first_name": "Sarah",
      "last_name": "Ade",
      "role": "sub_admin"
    }
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid token OR caller is not `super_admin` |
| `404 Not Found` | Submission not found |
| `404 Not Found` | Target admin ID not found or that admin is inactive |

---

### 7. Update Submission Status

**`PATCH /api/v1/admin/submissions/{submission_id}/status`**

Updates the status of a submission.

- `super_admin` → can update any submission
- `sub_admin` → can only update submissions assigned to them

**Requires `Authorization: Bearer <token>` header.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The submission to update |

#### Request Body (JSON)

```json
{
  "status": "completed"
}
```

#### Valid Status Values

| Value | Description |
|---|---|
| `new` | Fresh, unassigned submission |
| `in_progress` | Being actively worked on |
| `pending_client_input` | Waiting for more info from client |
| `ai_generated` | AI draft ready, under human review |
| `completed` | Final CV delivered |
| `rejected` | Submission rejected |

#### Success Response — `200 OK`

Returns the full updated submission object:

```json
{
  "status": "success",
  "message": "Submission status updated successfully",
  "data": {
    "id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "status": "completed",
    ...
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | Status value is not one of the valid options |
| `401 Unauthorized` | Invalid / missing token |
| `403 Forbidden` | Sub-admin trying to update a submission not assigned to them |
| `404 Not Found` | Submission does not exist |

---

### 8. Get Conversation Messages (Admin)

**`GET /api/v1/admin/submissions/{submission_id}/messages`**

Loads the full chat history for a submission from the admin side.

- `super_admin` → can read messages on any submission
- `sub_admin` → can only read messages on their assigned submissions

**Requires `Authorization: Bearer <token>` header.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The submission to load messages for |

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Messages fetched successfully",
  "data": {
    "conversation_id": "018f0001-bbbb-7ccc-dddd-eeeefffff222",
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "submission_status": "in_progress",
    "messages": [
      {
        "id": "018f0002-cccc-7ddd-eeee-ffff00001111",
        "sender_type": "client",
        "sender_name": "John",
        "message": "Hi, I have uploaded my old CV as reference.",
        "attachments": null,
        "is_read": true,
        "created_at": "2026-08-22 10:35:00.000000+00:00"
      },
      {
        "id": "018f0003-dddd-7eee-ffff-000011112222",
        "sender_type": "staff",
        "sender_name": "Sarah Ade",
        "message": "Got it! We'll tailor it for you.",
        "attachments": [
          {
            "url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/chat_attachments/draft.pdf",
            "public_id": "ai_cv_generator/chat_attachments/draft",
            "original_filename": "draft.pdf",
            "resource_type": "raw",
            "format": "pdf",
            "bytes": 310000
          }
        ],
        "is_read": false,
        "created_at": "2026-08-22 11:00:00.000000+00:00"
      }
    ]
  }
}
```

> **Note**: For client-sent messages, `sender_name` is the client's `first_name`. For staff messages, it is the staff member's full name.

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `401 Unauthorized` | Invalid / missing token |
| `403 Forbidden` | Sub-admin accessing a submission not assigned to them |
| `404 Not Found` | Submission not found |
| `404 Not Found` | Conversation not yet created for this submission |

---

### 9. Send Message to Client (Admin)

**`POST /api/v1/admin/submissions/{submission_id}/messages`**

Allows a staff member to reply in a submission's chat. Accepts `multipart/form-data`. Supports text only, files only, or both. Files are uploaded automatically to Cloudinary.

- `super_admin` → can message on any submission
- `sub_admin` → can only message on their assigned submissions

**Requires `Authorization: Bearer <token>` header.**

#### Content Type

```
Content-Type: multipart/form-data
```

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | Target submission |

#### Request Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Form Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | ❌ | Text message (required if no files) |
| `files` | file(s) | ❌ | One or multiple files (required if no message) |

#### Example — Sending a message with a file (axios)

```js
const formData = new FormData();
formData.append("message", "Here is your completed CV draft. Please review!");
formData.append("files", draftCvFile);

await axios.post(
  `/api/v1/admin/submissions/${submissionId}/messages`,
  formData,
  {
    headers: {
      Authorization: `Bearer ${adminToken}`,
      "Content-Type": "multipart/form-data",
    },
  }
);
```

#### Success Response — `201 Created`

```json
{
  "status": "success",
  "message": "Message sent successfully",
  "data": {
    "id": "018f0005-ffff-7000-1111-222233334444",
    "sender_type": "staff",
    "sender_name": "Sarah Ade",
    "message": "Here is your completed CV draft. Please review!",
    "attachments": [
      {
        "url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/chat_attachments/final_cv.pdf",
        "public_id": "ai_cv_generator/chat_attachments/final_cv",
        "original_filename": "final_cv.pdf",
        "resource_type": "raw",
        "format": "pdf",
        "bytes": 420000
      }
    ],
    "is_read": false,
    "created_at": "2026-08-22 13:00:00.000000+00:00"
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | Neither message nor files provided |
| `401 Unauthorized` | Invalid / missing token |
| `403 Forbidden` | Sub-admin messaging on a submission not assigned to them |
| `404 Not Found` | Submission or conversation not found |

---

## Full Endpoint Reference Table

| Method | Path | Auth | Role Required | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/admin/auth/create-admin` | None | — | Create staff account |
| `POST` | `/api/v1/admin/auth/login` | None | — | Login, get JWT |
| `GET` | `/api/v1/admin/auth/profile` | Bearer JWT | Any admin | Get own profile |
| `GET` | `/api/v1/admin/submissions` | Bearer JWT | Any admin | List submissions (role-filtered) |
| `GET` | `/api/v1/admin/submissions/{id}` | Bearer JWT | Any admin | Get single submission |
| `PATCH` | `/api/v1/admin/submissions/{id}/assign` | Bearer JWT | `super_admin` only | Assign to staff |
| `PATCH` | `/api/v1/admin/submissions/{id}/status` | Bearer JWT | Any admin | Update status |
| `GET` | `/api/v1/admin/submissions/{id}/messages` | Bearer JWT | Any admin | Get chat messages |
| `POST` | `/api/v1/admin/submissions/{id}/messages` | Bearer JWT | Any admin | Send message to client |

---

## Setting Up Admin Auth in React (Axios Interceptor)

```js
// api/axiosAdmin.js
import axios from "axios";

const adminApi = axios.create({
  baseURL: "https://ai-cv-generator-be.onrender.com",
});

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("admin_token");
      window.location.href = "/admin/login";
    }
    return Promise.reject(error);
  }
);

export default adminApi;
```

---

## Role-Based UI Logic

Use the `role` field from the login response or profile to conditionally render UI:

```jsx
const isSuper = admin.role === "super_admin";

// Show "Assign Staff" button only for super admin
{isSuper && (
  <button onClick={handleAssign}>Assign to Staff</button>
)}

// Show only assigned submissions for sub_admin
// (the API handles this automatically — just call GET /submissions)
```

---

## Submission `raw_data` Object Reference

When displaying a submission's details in the admin dashboard, the `raw_data` field contains the full structured CV data:

```json
{
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field_of_study": "string | null",
      "start_date": "string",
      "end_date": "string | null",
      "description": "string | null"
    }
  ],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "start_date": "string",
      "end_date": "string | null",
      "description": "string | null"
    }
  ],
  "skills": ["string"],
  "certifications": [
    {
      "name": "string",
      "issuing_organization": "string",
      "issue_date": "string | null",
      "expiration_date": "string | null"
    }
  ],
  "custom_notes": "string | null"
}
```
