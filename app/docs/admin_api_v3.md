# AI CV Generator — Admin API v3 Documentation

> **For the Admin Dashboard Frontend Team (React JS)**
> **Base URL:** `https://ai-cv-generator-be.onrender.com`
> **API Version:** `v1`
> All admin endpoints require `Authorization: Bearer <JWT_TOKEN>` unless stated otherwise.

---

## What's New in v3

This document covers **all new and modified endpoints** since v2. If you haven't read v2, start there — this doc only covers deltas and new additions.

| Feature | Where |
|---|---|
| 🆕 `PATCH /submissions/{id}/resume-text` | Save the candidate's plain-text resume to the submission |
| 🆕 `PATCH /submissions/{id}/job-description` | Update or clear the job description for a tailoring cycle |
| 🆕 `POST /submissions/{id}/tailor` | **One-click Tailor Resume** — generates CV + cover letter, renders 4 files (PDF + DOCX × 2), uploads to Cloudinary, returns download links |
| 🆕 `POST /auth/forgot-password` | Magic-link password reset — step 1 |
| 🆕 `POST /auth/reset-password` | Magic-link password reset — step 2 |
| 🆕 `GET /ai/models` | Dropdown of available OpenAI models for the Tailor page |
| ✏️ `POST /public/submissions` | Intake form now accepts many new fields (demographics, references, preferences) |
| ✏️ `POST /submissions/{id}/documents/render` | Now accepts `document_kind` field (`"resume"` or `"cover_letter"`) |
| ✏️ Submission object | Two new fields: `saved_resume_text` and `job_description` (admin-writeable) |

---

## Submission Object — What Changed in v3

Two new fields are now included on every full submission object returned by admin endpoints:

| New Field | Type | Who writes it | Description |
|---|---|---|---|
| `saved_resume_text` | `string \| null` | Sub-admin via `PATCH /resume-text` | The candidate's plain-text resume, saved permanently on the submission. This is the **primary source** the AI uses for tailoring. |
| `job_description` | `string \| null` | Sub-admin via `PATCH /job-description` (or client at intake) | The job description for the current application. Can be updated and cleared between tailoring cycles. |

These fields appear in the full submission detail response alongside `target_position`, `target_company`, `priority`, and `raw_data`.

---

## Tailor Resume Workflow — How It All Fits Together

Before calling `POST /tailor`, the sub-admin must complete two preparatory steps. The UI should enforce this order:

```
Step 1 ──► PATCH /submissions/{id}/resume-text
           (paste & save the candidate's resume text — once per submission)

Step 2 ──► PATCH /submissions/{id}/job-description
           (paste the job description for this specific application)

Step 3 ──► POST /submissions/{id}/tailor
           (generate CV + cover letter → 4 files rendered → all download links returned)

After Done ─► PATCH /submissions/{id}/job-description  { "job_description": null }
              (clear the JD so the next cycle starts clean)
```

> **Key principle:** `saved_resume_text` is persistent across multiple tailoring cycles. The sub-admin only pastes it **once** per submission. `job_description` is cycle-specific and should be cleared after each use.

---

## 🆕 Save Resume Text

### `PATCH /api/v1/admin/submissions/{submission_id}/resume-text`

Saves the candidate's plain-text resume permanently against the submission. This becomes the **primary source** the AI reads when tailoring. Call this once — or again if the resume changes.

**Auth:** `Bearer JWT` (any authenticated admin/sub-admin)
**RBAC:** Sub-admin must be **assigned** to this submission. Super admin can call for any submission.

#### Request Body

```json
{
  "saved_resume_text": "Jane Render | Senior Software Engineer\n\nEXPERIENCE\nSenior Backend Engineer — Acme Corp (2020–Present)\n• Reduced API latency by 40% via Redis caching strategy\n• Led migration of monolith to FastAPI microservices (6-person team)\n\nEDUCATION\nB.S. Computer Science — MIT, May 2016\n\nSKILLS\nPython, FastAPI, PostgreSQL, Redis, Docker, AWS"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `saved_resume_text` | string | ✅ Yes | Minimum 1 character. Cannot be blank. |

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "status_code": 200,
  "message": "Resume text saved successfully",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "saved_resume_text": "Jane Render | Senior Software Engineer\n\n..."
  }
}
```

#### Side Effects

- Creates a `resume_text_saved` activity in the submission's timeline with title `"Resume Text Saved"`.
- The text is immediately available as context for the next `POST /tailor` call.

#### Error Responses

| HTTP Status | Body `detail.message` | When it happens |
|---|---|---|
| `401 Unauthorized` | `"Could not validate credentials"` | Missing or expired token |
| `403 Forbidden` | `"You are not assigned to this submission"` | Sub-admin calling on an unassigned submission |
| `404 Not Found` | `"Submission not found"` | Invalid `submission_id` |
| `422 Unprocessable Entity` | Validation error array | `saved_resume_text` is empty or missing |

---

## 🆕 Update Job Description

### `PATCH /api/v1/admin/submissions/{submission_id}/job-description`

Updates or clears the job description for the current tailoring cycle. This field is **cycle-specific** — clear it after each tailoring session by passing `null` or an empty string.

**Auth:** `Bearer JWT`
**RBAC:** Same as resume-text — sub-admin must be assigned.

#### Request Body — Set

```json
{
  "job_description": "We are looking for a Senior Software Engineer to join our platform team. You will design and build high-throughput REST APIs using Python and FastAPI. Requirements: 5+ years backend experience, PostgreSQL, Redis, Docker."
}
```

#### Request Body — Clear (after clicking DONE)

```json
{
  "job_description": null
}
```

Or equivalently:

```json
{
  "job_description": ""
}
```

> Both `null` and `""` (empty string) clear the field. The response will confirm with `"job description cleared successfully"`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `job_description` | `string \| null` | ✅ Yes | Pass `null` or `""` to clear. No minimum length on the field itself. |

#### Success Response — After Setting `200 OK`

```json
{
  "status": "success",
  "status_code": 200,
  "message": "Job description updated successfully",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "job_description": "We are looking for a Senior Software Engineer..."
  }
}
```

#### Success Response — After Clearing `200 OK`

```json
{
  "status": "success",
  "status_code": 200,
  "message": "Job description cleared successfully",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "job_description": null
  }
}
```

#### Side Effects

- Creates a `job_description_updated` activity with title `"Job Description Updated"` when set.
- Creates a `job_description_updated` activity with title `"Job Description Cleared"` when cleared.
- Both activity types are logged — useful for audit trail display.

#### Error Responses

| HTTP Status | Body `detail.message` | When |
|---|---|---|
| `401` | `"Could not validate credentials"` | Missing/expired token |
| `403` | `"You are not assigned to this submission"` | Sub-admin on unassigned submission |
| `404` | `"Submission not found"` | Invalid `submission_id` |

---

## 🆕 Tailor Resume — One-Click Generation

### `POST /api/v1/admin/submissions/{submission_id}/tailor`

This is the **main action button** on the submission workspace. It does everything in a single call:

1. Validates the submission has resume content (`saved_resume_text` or `raw_data`).
2. Auto-selects the best AI prompt template based on the candidate's target role.
3. Calls the LLM (OpenAI or Gemini) **once** — returning both the CV and the cover letter in one JSON response.
4. Validates both outputs against the CV and cover letter schemas.
5. Renders **4 files**: resume PDF, resume DOCX, cover letter PDF, cover letter DOCX.
6. Uploads all 4 to Cloudinary.
7. Returns all download links in one response.
8. Updates the submission status to `"review"` automatically.
9. Broadcasts a `resume_tailored` WebSocket event to all connected clients on this submission.

**Auth:** `Bearer JWT`
**RBAC:** Sub-admin must be assigned. Super admin works for any submission.

#### Pre-condition Check

Before calling this endpoint, make sure:
- `saved_resume_text` is set **OR** `raw_data` was provided at intake. If neither exists, the API returns `400`.

#### Request Body

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "prompt_id": null,
  "custom_instructions": "Emphasise the 40% latency reduction metric. Highlight AWS certifications prominently.",
  "include_chat_history": true
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `provider` | string | ❌ | `"openai"` | LLM provider. Options: `"openai"` or `"gemini"`. Smart fallback: if the requested provider's key is missing, it silently falls back to the other. |
| `model` | string \| null | ❌ | Server default | Specific model name. Use `GET /ai/models` to get the dropdown list. Examples: `"gpt-4o"`, `"gpt-4o-mini"`, `"gemini-1.5-flash"`. If `null`, uses the server's configured default. |
| `prompt_id` | string \| null | ❌ | Auto-selected | ID of a specific system prompt template. If `null`, the server uses **smart role matching** — it reads the submission's `target_position` and selects the most relevant active prompt automatically. |
| `custom_instructions` | string \| null | ❌ | `null` | Extra instructions injected into the AI context. Use this to highlight specific metrics, achievements, or formatting preferences for this generation run. |
| `include_chat_history` | boolean | ❌ | `true` | Whether to include the client-admin conversation transcript as additional context for the AI. Usually leave this `true`. |

#### Smart Prompt Selection Logic

When `prompt_id` is `null`, the server selects a prompt in this order:

1. **Exact category match** — if the prompt's `category` appears in `target_position` (e.g., target position contains "finance" and a prompt has category "Finance").
2. **Keyword category matching** — broad keyword sets are checked:
   - `Technology` — matches: software, engineer, developer, backend, frontend, devops, cloud, data, security, etc.
   - `Product` — matches: product manager, scrum, agile, owner, BA, delivery, etc.
   - `Executive` — matches: director, VP, CTO, CEO, head of, principal, founder, etc.
   - `Marketing` — matches: marketing, growth, SEO, content, brand, social media, sales, etc.
3. **Fallback** — first available active prompt if no keyword match.

#### Success Response — `200 OK` (HTTP) / `201` in body

> Note: The HTTP response code is always `200` for success. The body `status_code` field carries `201` for a successful tailor. Check `status === "success"` and `data.documents.length > 0`.

```json
{
  "status": "success",
  "status_code": 201,
  "message": "Resume tailored successfully — 4 file(s) ready for download",
  "data": {
    "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "model": "gpt-4o",
    "provider_used": "openai",
    "input_tokens": 1850,
    "output_tokens": 920,
    "cost": 0.0138,
    "documents": [
      {
        "id": "018f4b10-1111-7222-3333-444455556666",
        "file_name": "Jane.pdf",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/.../resume_pdf_v1.pdf",
        "file_type": "pdf",
        "document_kind": "resume",
        "version": 1
      },
      {
        "id": "018f4b11-1111-7222-3333-444455556666",
        "file_name": "Jane.docx",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/.../resume_docx_v1.docx",
        "file_type": "docx",
        "document_kind": "resume",
        "version": 1
      },
      {
        "id": "018f4b12-1111-7222-3333-444455556666",
        "file_name": "Jane_cover_letter.pdf",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/.../cover_letter_pdf_v1.pdf",
        "file_type": "pdf",
        "document_kind": "cover_letter",
        "version": 1
      },
      {
        "id": "018f4b13-1111-7222-3333-444455556666",
        "file_name": "Jane_cover_letter.docx",
        "file_url": "https://res.cloudinary.com/demo/raw/upload/v1/.../cover_letter_docx_v1.docx",
        "file_type": "docx",
        "document_kind": "cover_letter",
        "version": 1
      }
    ]
  }
}
```

#### Document Object Fields

| Field | Type | Values | Description |
|---|---|---|---|
| `id` | string | UUID | Document record ID |
| `file_name` | string | `"Jane.pdf"`, `"Jane_cover_letter.docx"` | File name — client's first name + optional suffix + extension |
| `file_url` | string | Cloudinary URL | Direct download URL (or use the download endpoint below) |
| `file_type` | string | `"pdf"`, `"docx"` | Output format |
| `document_kind` | string | `"resume"`, `"cover_letter"` | Which document this is |
| `version` | integer | `1`, `2`, `3`… | Increments each time you call `/tailor` for the same submission |

#### Side Effects

- Submission `status` → `"review"` (automatically).
- A `status_changed` activity with title `"Resume Tailored"` is logged in the timeline.
- Prompt `usage_count` is incremented by 1 on the selected prompt template.
- WebSocket event `resume_tailored` is broadcast on `/api/v1/admin/submissions/{id}/ws`.

#### WebSocket Event

```json
{
  "event": "resume_tailored",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
    "model": "gpt-4o",
    "documents": [ ... ],
    "generated_by": "Sarah Johnson"
  }
}
```

#### Error Responses

| HTTP Status | Body `detail.message` | When |
|---|---|---|
| `400 Bad Request` | `"No resume content found. Please save the candidate's resume text before tailoring."` | Neither `saved_resume_text` nor `raw_data` exists on the submission |
| `401 Unauthorized` | `"Could not validate credentials"` | Missing or expired token |
| `403 Forbidden` | `"You are not assigned to this submission"` | Sub-admin on unassigned submission |
| `404 Not Found` | `"Submission not found"` | Invalid `submission_id` |
| `422 Unprocessable Entity` | `"AI CV output failed schema validation: ..."` | LLM returned malformed JSON — rare |
| `500 Internal Server Error` | `"AI generation failed: ..."` | Unexpected LLM error |
| `503 Service Unavailable` | `"No AI provider API key is configured..."` | Neither `OPENAI_API_KEY` nor `GEMINI_API_KEY` is set on the server |

---

## Updated: Document Render Endpoint

### `POST /api/v1/admin/submissions/{submission_id}/documents/render`

This endpoint already existed (see v2 docs). In v3, a new field `document_kind` has been added to the request body.

#### Updated Request Body

```json
{
  "ai_generation_id": "018f4a50-aaaa-7bbb-cccc-111122223333",
  "formats": ["pdf", "docx"],
  "document_kind": "resume"
}
```

| Field | Type | Required | Default | Values |
|---|---|---|---|---|
| `ai_generation_id` | string | ✅ Yes | — | ID from a prior generation run |
| `formats` | array | ❌ | `["pdf", "docx"]` | Any combination of `"pdf"` and `"docx"` |
| `document_kind` | string | ❌ | `"resume"` | `"resume"` or `"cover_letter"` |

> **Note:** The `/tailor` endpoint already renders all 4 files automatically. Use this endpoint only if you need to re-render a specific document kind from a prior AI generation record (e.g., re-render just the cover letter PDF after a template update).

---

## 🆕 Get Available AI Models

### `GET /api/v1/admin/ai/models`

Returns a curated list of available OpenAI chat models for the Tailor Resume model-selection dropdown. Each entry includes a human-readable label, a tier badge, and a cost hint.

**Auth:** `Bearer JWT` (any admin role)

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "status_code": 200,
  "message": "6 chat model(s) available",
  "data": {
    "models": [
      {
        "id": "gpt-4o",
        "label": "GPT-4o",
        "tier": "recommended",
        "note": "Best quality — fast"
      },
      {
        "id": "gpt-4o-mini",
        "label": "GPT-4o Mini",
        "tier": "standard",
        "note": "Fast & cost-efficient"
      },
      {
        "id": "gpt-4-turbo",
        "label": "GPT-4 Turbo",
        "tier": "standard",
        "note": "Long-context tasks"
      },
      {
        "id": "gpt-3.5-turbo",
        "label": "GPT-3.5 Turbo",
        "tier": "budget",
        "note": "Fastest — testing only"
      }
    ],
    "source": "openai_api"
  }
}
```

#### Model Object Fields

| Field | Type | Values | Description |
|---|---|---|---|
| `id` | string | e.g. `"gpt-4o"` | Pass this as `model` in the tailor request body |
| `label` | string | Human-readable | Display name for the dropdown UI |
| `tier` | string | `"recommended"`, `"standard"`, `"budget"` | Use this to style or sort the dropdown |
| `note` | string | Short description | Show as tooltip or sublabel in the dropdown |
| `source` | string | `"openai_api"`, `"curated"` | `"curated"` means the API was unreachable; the server returned a hardcoded list. Not a model field — top-level in `data`. |

#### Tier Styling Guide

```jsx
const tierStyles = {
  recommended: "text-green-700 font-semibold",
  standard:    "text-gray-700",
  budget:      "text-orange-600 text-sm",
};
```

> **Graceful fallback:** If the OpenAI API is unreachable or the key is missing, the server always returns the curated list. `source` will be `"curated"`. The dropdown will never be empty.

#### Error Responses

| HTTP Status | When |
|---|---|
| `401 Unauthorized` | Missing or invalid token |

---

## 🆕 Password Reset — Magic Link Flow

Two new endpoints power the forgot password / reset password feature for admin accounts.

### Step 1 — Request Reset Email

### `POST /api/v1/admin/auth/forgot-password`

Sends a password reset email with a magic link to the registered email address. Available for `super_admin` and `sub_admin` roles only.

**Auth:** None required.

> **Security note:** This endpoint always returns `200 OK` with the same generic message regardless of whether the email exists. This prevents attackers from discovering which emails are registered (enumeration protection). Do not try to infer account existence from the response.

#### Request Body

```json
{
  "email": "sarah.johnson@company.com"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `email` | string (email) | ✅ Yes | Must be a valid email format — `422` otherwise |

#### Success Response — `200 OK` (always)

```json
{
  "status": "success",
  "status_code": 200,
  "message": "If that email is registered, a reset link has been sent."
}
```

#### What Happens Behind the Scenes

1. The server looks up the email — only active `super_admin` or `sub_admin` accounts qualify.
2. A JWT reset token is generated with a **30-minute expiry**.
3. The token is stored on the admin record (`reset_token`, `reset_token_expires_at`).
4. An email is dispatched containing a link to your frontend reset page:
   `https://your-dashboard.com/reset-password?token=<token>`
5. The frontend reads `?token=` from the URL and passes it to step 2.

#### Error Responses

| HTTP Status | When |
|---|---|
| `422 Unprocessable Entity` | `email` field is missing or not a valid email format |

---

### Step 2 — Submit New Password

### `POST /api/v1/admin/auth/reset-password`

Validates the magic-link token and sets the new password. On success, returns a fresh `access_token` so the frontend can redirect the user straight into their dashboard — no separate login step required.

**Auth:** None required (the token in the body authenticates the request).

#### Request Body

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "MyNewSecurePassword456!"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `token` | string | ✅ Yes | JWT reset token from the magic link URL |
| `new_password` | string | ✅ Yes | Minimum 8 characters |

#### Success Response — `200 OK`

```json
{
  "status": "success",
  "status_code": 200,
  "message": "Password reset successfully. Welcome back!",
  "data": {
    "id": "018f0010-aaaa-7bbb-cccc-ddddeeee1111",
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@company.com",
    "role": "sub_admin",
    "is_active": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

> **Important:** After a successful reset, store the `access_token` and use it for all subsequent requests. The old token (if any) remains valid until it expires naturally — consider redirecting to the dashboard immediately.

> **Token is single-use:** The `reset_token` is cleared from the database on first successful use. Submitting the same token a second time returns a `400` error.

#### Error Responses

| HTTP Status | Body `detail.message` | When |
|---|---|---|
| `400 Bad Request` | `"This reset link is invalid or has expired. Please request a new one."` | Token is forged, malformed, or JWT-expired |
| `400 Bad Request` | `"This reset link has already been used. Please request a new one."` | Token was already consumed (single-use) |
| `400 Bad Request` | `"This reset link has expired. Please request a new one."` | Token is valid JWT but the DB expiry timestamp has passed (30-min window) |
| `422 Unprocessable Entity` | Validation errors | Missing fields or `new_password` shorter than 8 characters |

---

## Updated: Public Intake Form

### `POST /api/v1/public/submissions`

The client intake form has been **significantly expanded**. Dozens of new optional fields have been added. Only `first_name`, `last_name`, and `email` are required — everything else is optional.

> **Backward compatible:** If your existing form only sends the original minimal fields, it still works. Nothing broke.

#### Full Request Body

```json
{
  "first_name": "Jane",
  "last_name": "Render",
  "middle_name": null,
  "email": "jane.render@example.com",
  "date_of_birth": "1992-06-15",

  "phone": "+1 555 000 0000",
  "address_line": "123 Main Street, Apt 4B",
  "city": "San Francisco",
  "state": "CA",
  "country": "United States",
  "zip_code": "94105",

  "linkedin_url": "https://linkedin.com/in/janerender",
  "portfolio_url": "https://github.com/janerender",

  "resume_file_url": "https://res.cloudinary.com/demo/raw/upload/resumes/jane_render_resume.pdf",
  "resume_file_name": "jane_render_resume.pdf",

  "desired_job_titles": ["Senior Software Engineer", "Staff Engineer", "Backend Lead"],
  "preferred_work_arrangement": "remote",
  "expected_salary_range": "$140k–$170k",
  "available_start_date": "2026-10-01",
  "companies_to_exclude": ["Amazon", "Meta"],

  "security_clearance": "none",
  "citizenship_status": "US Citizen",
  "visa_sponsorship_required": "no",
  "non_compete_obligations": "No active non-compete agreements.",

  "professional_references": [
    {
      "name": "John Smith",
      "email": "john.smith@company.com",
      "phone": "+1 555 111 2222",
      "company": "Acme Corp"
    }
  ],

  "gender": "female",
  "sexual_orientation": "prefer_not_to_say",
  "race_ethnicity": "prefer_not_to_say",
  "veteran_status": "not_a_veteran",
  "has_disability": "prefer_not_to_say",

  "notes": "Please focus on backend engineering roles. I'm open to startup environments.",

  "raw_data": {
    "education": [
      {
        "institution": "MIT",
        "degree": "B.S. Computer Science",
        "start_date": "2010-09-01",
        "end_date": "2014-06-01"
      }
    ],
    "experience": [
      {
        "company": "Acme Corp",
        "role": "Senior Backend Engineer",
        "start_date": "2020-01-01"
      }
    ],
    "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
    "certifications": [
      {
        "name": "AWS Certified Solutions Architect",
        "issuing_organization": "Amazon Web Services",
        "issue_date": "2023-03-01"
      }
    ],
    "custom_notes": "7+ years of backend engineering experience"
  },

  "target_position": "Senior Software Engineer",
  "target_company": "Stripe",
  "job_description": "We are looking for a Senior Engineer to build payment infrastructure...",
  "priority": "normal"
}
```

#### Enum Reference Tables

All enum fields below accept **only the exact string values listed**. Sending anything else returns a `422` validation error.

---

##### `preferred_work_arrangement`

| Value | Display Label |
|---|---|
| `"remote"` | Remote |
| `"hybrid"` | Hybrid |
| `"onsite"` | On-site |
| `"flexible"` | Flexible |

---

##### `security_clearance`

| Value | Display Label |
|---|---|
| `"none"` | None |
| `"confidential"` | Confidential |
| `"secret"` | Secret |
| `"top_secret"` | Top Secret |
| `"top_secret_sci"` | Top Secret / SCI |
| `"other"` | Other |

---

##### `visa_sponsorship_required`

| Value | Display Label |
|---|---|
| `"yes"` | Yes, I need sponsorship |
| `"no"` | No, I do not need sponsorship |
| `"not_applicable"` | Not applicable |

---

##### `gender` (voluntary / EEO)

| Value | Display Label |
|---|---|
| `"male"` | Male |
| `"female"` | Female |
| `"non_binary"` | Non-binary |
| `"prefer_not_to_say"` | Prefer not to say |
| `"other"` | Other |

---

##### `sexual_orientation` (voluntary / EEO)

| Value | Display Label |
|---|---|
| `"heterosexual"` | Heterosexual / Straight |
| `"gay_or_lesbian"` | Gay or Lesbian |
| `"bisexual"` | Bisexual |
| `"prefer_not_to_say"` | Prefer not to say |
| `"other"` | Other |

---

##### `race_ethnicity` (voluntary / EEO)

| Value | Display Label |
|---|---|
| `"american_indian_or_alaska_native"` | American Indian or Alaska Native |
| `"asian"` | Asian |
| `"black_or_african_american"` | Black or African American |
| `"hispanic_or_latino"` | Hispanic or Latino |
| `"native_hawaiian_or_pacific_islander"` | Native Hawaiian or Pacific Islander |
| `"white"` | White |
| `"two_or_more_races"` | Two or More Races |
| `"prefer_not_to_say"` | Prefer not to say |
| `"other"` | Other |

---

##### `veteran_status` (voluntary / EEO)

| Value | Display Label |
|---|---|
| `"not_a_veteran"` | Not a Veteran |
| `"veteran"` | Veteran |
| `"active_duty"` | Active Duty |
| `"prefer_not_to_say"` | Prefer not to say |

---

##### `has_disability` (voluntary / EEO)

| Value | Display Label |
|---|---|
| `"yes"` | Yes |
| `"no"` | No |
| `"prefer_not_to_say"` | Prefer not to say |

---

##### `priority` (submission)

| Value | Display Label | Badge Color |
|---|---|---|
| `"low"` | Low | Gray |
| `"normal"` | Normal | Blue |
| `"high"` | High | Red |

---

#### Unchanged Success Response — `200 OK`

```json
{
  "status": "success",
  "status_code": 201,
  "message": "Submission created successfully. Use your access token to track this request.",
  "data": {
    "submission_id": "018f4a2b-1c3d-7e8f-9a0b-1c2d3e4f5a6b",
    "reference_id": "SUB-2026-042",
    "access_token": "018f4a2c-aaaa-7bbb-cccc-111122223333",
    "status": "new",
    "client": {
      "id": "018f0000-aaaa-7bbb-cccc-ddddeeee1111",
      "first_name": "Jane",
      "middle_name": null,
      "last_name": "Render",
      "email": "jane.render@example.com",
      "phone": "+1 555 000 0000",
      "city": "San Francisco",
      "state": "CA",
      "country": "United States",
      "linkedin_url": "https://linkedin.com/in/janerender",
      "portfolio_url": "https://github.com/janerender",
      "resume_file_url": "https://res.cloudinary.com/demo/.../jane_render_resume.pdf",
      "resume_file_name": "jane_render_resume.pdf",
      "desired_job_titles": ["Senior Software Engineer", "Staff Engineer"],
      "preferred_work_arrangement": "remote",
      "expected_salary_range": "$140k–$170k",
      "citizenship_status": "US Citizen",
      "visa_sponsorship_required": "no",
      "veteran_status": "not_a_veteran"
    }
  }
}
```

---

## Updated: New Activity Types in v3

The `activity_type` field on activity objects now includes two additional values:

| `activity_type` | When it is logged | `actor_name` present? |
|---|---|---|
| `submission_created` | Automatically on new submission | ❌ No |
| `assigned` | On assignment or unassignment | ✅ Yes |
| `status_changed` | On any status change (including auto-escalation and tailor) | ✅ Yes |
| `resume_text_saved` | 🆕 When sub-admin saves resume text | ✅ Yes |
| `job_description_updated` | 🆕 When JD is set or cleared | ✅ Yes |

---

## Full Endpoint Reference — v3 Additions

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `PATCH` | `/api/v1/admin/submissions/{id}/resume-text` | Bearer JWT | Assigned sub-admin or super admin | Save candidate's resume text |
| `PATCH` | `/api/v1/admin/submissions/{id}/job-description` | Bearer JWT | Assigned sub-admin or super admin | Set or clear job description |
| `POST` | `/api/v1/admin/submissions/{id}/tailor` | Bearer JWT | Assigned sub-admin or super admin | One-click: generate CV + cover letter + 4 files |
| `GET` | `/api/v1/admin/ai/models` | Bearer JWT | Any | Model dropdown for tailor page |
| `POST` | `/api/v1/admin/auth/forgot-password` | None | — | Request magic-link password reset |
| `POST` | `/api/v1/admin/auth/reset-password` | None | — | Validate token + set new password |

---

## React Integration Patterns

### Tailor Resume Page — Full Flow

```jsx
import { useState, useEffect } from "react";
import axios from "axios";

const BASE = "https://ai-cv-generator-be.onrender.com/api/v1/admin";

function TailorResumePage({ submissionId, token }) {
  const headers = { Authorization: `Bearer ${token}` };

  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("gpt-4o");
  const [customInstructions, setCustomInstructions] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState([]);

  // 1. Load model dropdown on mount
  useEffect(() => {
    axios.get(`${BASE}/ai/models`, { headers }).then(({ data }) => {
      setModels(data.data.models);
    });
  }, []);

  // 2. Save resume text (call once when admin pastes it)
  const saveResumeText = async (text) => {
    await axios.patch(
      `${BASE}/submissions/${submissionId}/resume-text`,
      { saved_resume_text: text },
      { headers }
    );
  };

  // 3. Update job description
  const updateJobDescription = async (jd) => {
    await axios.patch(
      `${BASE}/submissions/${submissionId}/job-description`,
      { job_description: jd || null },
      { headers }
    );
  };

  // 4. Tailor (main action)
  const handleTailor = async () => {
    setIsLoading(true);
    try {
      const { data } = await axios.post(
        `${BASE}/submissions/${submissionId}/tailor`,
        {
          provider: "openai",
          model: selectedModel,
          custom_instructions: customInstructions || null,
          include_chat_history: true,
        },
        { headers }
      );

      if (data.status === "success") {
        setDocuments(data.data.documents);
        // Submission status is now "review" — update local state
      }
    } catch (err) {
      const status = err.response?.status;
      const message = err.response?.data?.detail?.message;
      if (status === 400) alert(`Missing resume content: ${message}`);
      if (status === 503) alert("AI service unavailable — no API key configured");
    } finally {
      setIsLoading(false);
    }
  };

  // 5. Clear job description after done
  const clearJobDescription = () => updateJobDescription(null);

  return (
    <div>
      {/* Model selector */}
      <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label} — {m.note}
            {m.tier === "recommended" ? " ⭐" : ""}
          </option>
        ))}
      </select>

      <textarea
        placeholder="Additional instructions (optional)..."
        value={customInstructions}
        onChange={(e) => setCustomInstructions(e.target.value)}
      />

      <button onClick={handleTailor} disabled={isLoading}>
        {isLoading ? "Tailoring..." : "⚡ Tailor Resume"}
      </button>

      {/* Documents grid */}
      {documents.map((doc) => (
        <a key={doc.id} href={doc.file_url} target="_blank" rel="noreferrer">
          ⬇ {doc.document_kind === "resume" ? "Resume" : "Cover Letter"}{" "}
          {doc.file_type.toUpperCase()} v{doc.version}
        </a>
      ))}
    </div>
  );
}
```

---

### Password Reset Flow

```jsx
// Step 1: Forgot Password form
async function requestPasswordReset(email) {
  // Always returns 200 — no need to check for "email not found" case
  const { data } = await axios.post(
    `${BASE.replace("/admin", "")}/admin/auth/forgot-password`,
    { email }
  );
  // Show: "If that email is registered, a reset link has been sent."
  alert(data.message);
}

// Step 2: Reset Password form (user lands here from email link)
// URL: /reset-password?token=eyJ...
async function submitNewPassword(token, newPassword) {
  try {
    const { data } = await axios.post(
      `${BASE.replace("/admin", "")}/admin/auth/reset-password`,
      { token, new_password: newPassword }
    );

    // Store the new token and redirect to dashboard
    localStorage.setItem("admin_token", data.data.access_token);
    window.location.href = "/admin/dashboard";
  } catch (err) {
    const message = err.response?.data?.detail?.message;
    // Show specific error: "already used", "expired", "invalid"
    alert(message || "Reset failed. Please request a new link.");
  }
}
```

---

### Document Kind Badge

```jsx
const kindConfig = {
  resume:       { label: "Resume",       icon: "📄", color: "bg-blue-100 text-blue-700"   },
  cover_letter: { label: "Cover Letter", icon: "✉️", color: "bg-purple-100 text-purple-700" },
};

function DocumentKindBadge({ kind }) {
  const config = kindConfig[kind] || kindConfig.resume;
  return (
    <span className={`badge ${config.color}`}>
      {config.icon} {config.label}
    </span>
  );
}
```

---

## Common Mistakes to Avoid in v3

| Mistake | Fix |
|---|---|
| Calling `/tailor` without saving resume text first | Check `saved_resume_text` is non-null before showing the Tailor button. If null, prompt the sub-admin to paste the resume. |
| Forgetting to clear `job_description` between cycles | After the sub-admin clicks "Done", call `PATCH /job-description` with `null`. |
| Expecting HTTP `201` from `/tailor` | The HTTP status is always `200`. Check `data.status === "success"` and `data.data.documents.length > 0` instead. |
| Not handling the `503` from `/tailor` | Show a user-friendly message: "AI service is not configured. Contact your system administrator." |
| Displaying all documents in one flat list | Filter by `document_kind` — show resume files and cover letter files in separate sections. |
| Sending the reset token to `/forgot-password` instead of `/reset-password` | Step 1 only needs the email. Step 2 needs the token + new password. They are separate endpoints. |
| Assuming `forgot-password` 200 means the email exists | It always returns 200. Never show "email registered" or "email not found" to the user. |
| Ignoring `source: "curated"` on the models list | If `source === "curated"`, the live API was unreachable. Consider showing a subtle note in the UI. |
| Using the `raw_data` structured fields as primary AI source | `saved_resume_text` takes priority for AI tailoring. `raw_data` is a fallback only. |
