# AI CV Generator — Client API Documentation

> **For the Frontend Team (React JS)**
> Base URL: `https://ai-cv-generator-be.onrender.com`
> All endpoints return JSON. All timestamps are UTC strings.

---

## Overview

The backend has **two separate worlds**:

| World | Who uses it | Auth method | Base path |
|---|---|---|---|
| **Public Client API** | End-users requesting CV generation | `X-Client-Access-Token` header | `/api/v1/public/` |
| **Admin API** | Staff / Admins managing requests | `Bearer JWT` in `Authorization` header | `/api/v1/admin/` |
| **Upload API** | Anyone uploading files | No auth required | `/api/v1/public/upload` |

---

## Standard Response Shape

Every single response from this API — success or error — follows this envelope:

```json
{
  "status": "success" | "error",
  "message": "Human-readable message",
  "data": { ... }
}
```

**Error responses** look like this:

```json
{
  "status": "error",
  "message": "Submission not found or access token is invalid",
  "data": null
}
```

---

## How Client Auth Works (Important — Read This First)

Clients do **not** have accounts and do **not** log in. The flow is:

1. Client submits their CV request → `POST /api/v1/public/submissions`
2. Backend returns a `submission_id` and a secret `access_token`
3. **Frontend must save both** (localStorage is fine) — they are the client's identity
4. All subsequent client requests require `submission_id` in the URL **and** the `access_token` in the `X-Client-Access-Token` header

```
X-Client-Access-Token: 018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b
```

---

## Client Endpoints

---

### 1. Create a Submission

**`POST /api/v1/public/submissions`**

This is the entry point. The client fills in their details and CV data. The backend creates a client profile (or finds existing one by email), creates the submission, and opens a conversation thread automatically.

**No auth required.**

#### Request Body (JSON)

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+2348012345678",
  "target_position": "Senior Backend Engineer",
  "job_description": "We are looking for a backend engineer with 5+ years experience in Python...",
  "existing_cv_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/resumes/old_cv.pdf",
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
  }
}
```

#### Field Reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `first_name` | string | ✅ | |
| `last_name` | string | ✅ | |
| `email` | string (email) | ✅ | Used to look up or create client profile |
| `phone` | string | ❌ | |
| `target_position` | string | ✅ | The job role they want the CV for |
| `job_description` | string | ❌ | Paste the full JD for AI tailoring |
| `existing_cv_url` | string (URL) | ❌ | Cloudinary URL of an uploaded existing CV |
| `raw_data` | object | ✅ | See nested fields below |
| `raw_data.education` | array | ❌ | List of education history objects |
| `raw_data.experience` | array | ❌ | List of work experience objects |
| `raw_data.skills` | array of strings | ❌ | e.g. `["Python", "React"]` |
| `raw_data.certifications` | array | ❌ | List of certification objects |
| `raw_data.custom_notes` | string | ❌ | Any additional notes for the CV writer |

#### Success Response — `201 Created`

```json
{
  "status": "success",
  "message": "Submission created successfully. Use your access token to track this request.",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "access_token": "018f4a2b-0000-7111-aaaa-ccccddddeeee",
    "status": "new",
    "client": {
      "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com"
    }
  }
}
```

> **⚠️ Critical**: Save both `submission_id` and `access_token` immediately after this call. Without them, the client cannot access their submission again.

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | Missing required fields |
| `422 Unprocessable Entity` | Invalid email format or schema mismatch |

---

### 2. Get Submission Status

**`GET /api/v1/public/submissions/{submission_id}`**

Lets the client poll the current status of their CV request — whether it's new, being worked on, completed, etc.

**Requires `X-Client-Access-Token` header.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The ID returned from create submission |

#### Request Headers

```
X-Client-Access-Token: 018f4a2b-0000-7111-aaaa-ccccddddeeee
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Submission fetched successfully",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "status": "in_progress",
    "target_position": "Senior Backend Engineer",
    "created_at": "2026-08-22 10:30:00.000000+00:00",
    "updated_at": "2026-08-22 11:45:00.000000+00:00",
    "client": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com"
    },
    "assigned_to": {
      "first_name": "Sarah",
      "last_name": "Ade"
    }
  }
}
```

> `assigned_to` is `null` if no staff member has been assigned yet.

#### Submission Status Values

| Status | Meaning | What to show the user |
|---|---|---|
| `new` | Just submitted, not yet picked up | "Submitted — Awaiting Review" |
| `in_progress` | A staff member is actively working | "In Progress" |
| `pending_client_input` | Staff needs more info from client | "Action Required" |
| `ai_generated` | AI draft is ready for human review | "Almost Done" |
| `completed` | Final CV has been delivered | "Completed ✓" |
| `rejected` | Submission was rejected | "Rejected" |

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `404 Not Found` | Wrong `submission_id` or wrong `access_token` |

---

### 3. Get Conversation Messages

**`GET /api/v1/public/submissions/{submission_id}/messages`**

Fetches the full chat history between the client and the assigned staff member. Think of this as loading a WhatsApp conversation — it returns every message in chronological order.

**Requires `X-Client-Access-Token` header.**

#### URL Parameters

| Parameter | Type | Description |
|---|---|---|
| `submission_id` | string (UUID) | The submission to fetch messages for |

#### Request Headers

```
X-Client-Access-Token: 018f4a2b-0000-7111-aaaa-ccccddddeeee
```

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "message": "Messages fetched successfully",
  "data": {
    "conversation_id": "018f0001-bbbb-7ccc-dddd-eeeefffff222",
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "messages": [
      {
        "id": "018f0002-cccc-7ddd-eeee-ffff00001111",
        "sender_type": "client",
        "sender_name": "You",
        "message": "Hi, I have uploaded my old CV as reference.",
        "attachments": null,
        "is_read": true,
        "created_at": "2026-08-22 10:35:00.000000+00:00"
      },
      {
        "id": "018f0003-dddd-7eee-ffff-000011112222",
        "sender_type": "staff",
        "sender_name": "Sarah Ade",
        "message": "Got it! We'll tailor it to the Senior Backend Engineer role. Could you provide the full job description?",
        "attachments": [
          {
            "url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/chat_attachments/notes.pdf",
            "public_id": "ai_cv_generator/chat_attachments/notes",
            "original_filename": "notes.pdf",
            "resource_type": "raw",
            "format": "pdf",
            "bytes": 45000
          }
        ],
        "is_read": false,
        "created_at": "2026-08-22 11:00:00.000000+00:00"
      }
    ]
  }
}
```

#### Message Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique message ID |
| `sender_type` | `"client"` or `"staff"` | Who sent the message |
| `sender_name` | string | `"You"` for client messages, staff full name for staff messages |
| `message` | string | The text content |
| `attachments` | array or `null` | List of file objects (see Upload docs) |
| `is_read` | boolean | Whether the other party has read it |
| `created_at` | string | UTC timestamp |

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `404 Not Found` | Wrong submission ID, wrong token, or no conversation exists yet |

---

### 4. Send a Message

**`POST /api/v1/public/submissions/{submission_id}/messages`**

Sends a message from the client to the assigned staff member. This endpoint accepts `multipart/form-data` — you can send text only, files only, or both at the same time. Files are automatically uploaded to Cloudinary.

**Requires `X-Client-Access-Token` header.**

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
X-Client-Access-Token: 018f4a2b-0000-7111-aaaa-ccccddddeeee
```

#### Form Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | ❌ | The text message (required if no files) |
| `files` | file(s) | ❌ | One or multiple file attachments (required if no message) |

> At least one of `message` or `files` must be provided.

#### Example — Text only (axios)

```js
const formData = new FormData();
formData.append("message", "Here is more context about the role.");

await axios.post(
  `/api/v1/public/submissions/${submissionId}/messages`,
  formData,
  {
    headers: {
      "X-Client-Access-Token": accessToken,
      "Content-Type": "multipart/form-data",
    },
  }
);
```

#### Example — File + text (axios)

```js
const formData = new FormData();
formData.append("message", "Please use this updated CV.");
formData.append("files", file); // a File object from <input type="file">

await axios.post(
  `/api/v1/public/submissions/${submissionId}/messages`,
  formData,
  {
    headers: {
      "X-Client-Access-Token": accessToken,
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
    "id": "018f0004-eeee-7fff-0000-111122223333",
    "sender_type": "client",
    "message": "Please use this updated CV.",
    "attachments": [
      {
        "url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/chat_attachments/updated_cv.pdf",
        "public_id": "ai_cv_generator/chat_attachments/updated_cv",
        "original_filename": "updated_cv.pdf",
        "resource_type": "raw",
        "format": "pdf",
        "bytes": 180000
      }
    ],
    "is_read": false,
    "created_at": "2026-08-22 12:00:00.000000+00:00"
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | Neither message nor files provided |
| `404 Not Found` | Wrong submission ID or access token |

---

## File Upload Endpoint

**`POST /api/v1/public/upload`**

A standalone upload endpoint. Use this when you want to upload a file (e.g. an existing CV) **before** creating the submission, so you can include the `existing_cv_url` in the submission body.

**No auth required.**

#### Content Type

```
Content-Type: multipart/form-data
```

#### Form Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `files` | file(s) | ✅ | — | One or multiple files |
| `folder` | string | ❌ | `ai_cv_generator/uploads` | Cloudinary destination folder |

#### Supported File Types

| Type | Extensions |
|---|---|
| Documents | `.pdf`, `.doc`, `.docx` |
| Images | `.png`, `.jpg`, `.jpeg` |
| Videos | `.mp4` |

#### Example — Single file upload (axios)

```js
const formData = new FormData();
formData.append("files", file);
formData.append("folder", "ai_cv_generator/resumes");

const response = await axios.post("/api/v1/public/upload", formData, {
  headers: { "Content-Type": "multipart/form-data" },
});

const { url } = response.data.data; // use this as existing_cv_url
```

#### Success Response — Single File — `201 Created`

```json
{
  "status": "success",
  "message": "File uploaded successfully to Cloudinary",
  "data": {
    "url": "https://res.cloudinary.com/demo/raw/upload/v1600000000/ai_cv_generator/resumes/my_resume.pdf",
    "public_id": "ai_cv_generator/resumes/my_resume",
    "original_filename": "my_resume.pdf",
    "resource_type": "raw",
    "format": "pdf",
    "bytes": 245000
  }
}
```

#### Success Response — Multiple Files — `201 Created`

```json
{
  "status": "success",
  "message": "3 files uploaded successfully to Cloudinary",
  "data": {
    "total": 3,
    "files": [
      {
        "url": "https://res.cloudinary.com/demo/image/upload/v1/ai_cv_generator/uploads/photo.jpg",
        "public_id": "ai_cv_generator/uploads/photo",
        "original_filename": "photo.jpg",
        "resource_type": "image",
        "format": "jpg",
        "bytes": 52000
      }
    ]
  }
}
```

#### Error Responses

| HTTP Status | When it happens |
|---|---|
| `400 Bad Request` | No file attached to request |

---

## Health Check

**`GET /health`**

No auth. Use to verify the server is running.

```json
{
  "status": "healthy",
  "message": "Server is running smoothly"
}
```

---

## Recommended Client-Side Flow (Step by Step)

```
1. [Optional] User uploads existing CV
   POST /api/v1/public/upload
   → save returned `url` as existing_cv_url

2. User fills the submission form
   POST /api/v1/public/submissions
   → save submission_id + access_token to localStorage

3. User is redirected to a status/tracking page
   GET /api/v1/public/submissions/{submission_id}
   → poll this every 30s or on page load to update status badge

4. User opens the chat
   GET /api/v1/public/submissions/{submission_id}/messages
   → render all messages in a chat UI (poll every 5–10s for new messages)

5. User sends a message or file
   POST /api/v1/public/submissions/{submission_id}/messages
   → use multipart/form-data with message and/or files field
```

---

## Common Mistakes to Avoid

| Mistake | Fix |
|---|---|
| Sending JSON to the message endpoint | Use `multipart/form-data` — it accepts form fields, not JSON |
| Forgetting to save the `access_token` | Save it immediately after submission creation |
| Using `Authorization: Bearer` for client routes | Client routes use `X-Client-Access-Token` header, not Bearer |
| Not sending at least message or files | The send-message endpoint returns 400 if both are empty |
| Using wrong `Content-Type` for uploads | Always set `Content-Type: multipart/form-data` when sending files |
