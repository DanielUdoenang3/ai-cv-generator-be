# Real-Time Chat & WebSocket API Documentation

> **For the Frontend Team (React JS)**  
> This document details the hybrid REST/WebSocket real-time chat architecture implemented for both the **Public Client Interface** and the **Admin Dashboard**.

---

## 💡 Architecture Overview

To achieve reliable file uploads, robust input validation, and real-time responsiveness, the chat uses a **Hybrid REST + WebSocket Architecture**:

1. **State Mutations (Write Operations)**: Handled via standard HTTP REST requests. The frontend sends, edits, deletes, and marks messages as read using REST endpoints. This ensures clean support for multi-file attachments (via Cloudinary) and validation.
2. **Real-Time Delivery (Read Operations)**: Handled via WebSocket connections. The frontend establishes a persistent connection to listen to real-time events (`new_message`, `message_updated`, `message_deleted`, `typing`, etc.) broadcast by the backend.

---

## 🔑 Authentication

Browsers do not support custom headers (like `Authorization`) in native WebSocket handshakes. Therefore:
- The WebSocket auth token **must** be sent as a query parameter named `token`.
- If authentication fails, the server closes the connection with code `4001`.

---

## 👥 Public Client Side Integration

### 1. Connecting the WebSocket

Establish a connection to the following URL:

```
WS_URL = ws://<backend-host>/api/v1/public/submissions/{submission_id}/ws?token={access_token}
```

- **`submission_id`**: The ID of the submission.
- **`access_token`**: The access token returned during the submission creation (typically stored in `localStorage`).

---

### 2. Client REST Endpoints

All client requests require `X-Client-Access-Token` in the headers.

#### A. Fetch Message History
* **Endpoint**: `GET /api/v1/public/submissions/{submission_id}/messages`
* **Response**:
```json
{
  "status": "success",
  "message": "Messages fetched successfully",
  "data": {
    "conversation_id": "conv-uuid",
    "submission_id": "sub-uuid",
    "messages": [
      {
        "id": "msg-uuid",
        "sender_type": "client" | "staff",
        "sender_name": "You" | "Sarah Ade (Staff)",
        "message": "Hello!",
        "attachments": [],
        "is_read": true,
        "created_at": "2026-08-23T20:30:54Z",
        "updated_at": "2026-08-23T20:35:10Z"
      }
    ]
  }
}
```

#### B. Send Message
* **Endpoint**: `POST /api/v1/public/submissions/{submission_id}/messages`
* **Headers**: `Content-Type: multipart/form-data`
* **Form Data**:
  - `message` (string, optional): Message content.
  - `files` (file, optional, multiple): Upload files directly.
* **Response**:
```json
{
  "status": "success",
  "message": "Message sent successfully",
  "data": {
    "id": "msg-uuid",
    "sender_type": "client",
    "sender_name": "You",
    "message": "Hello!",
    "attachments": [],
    "is_read": false,
    "created_at": "2026-08-23T20:30:54Z",
    "updated_at": "2026-08-23T20:30:54Z"
  }
}
```

#### C. Edit Message
* **Endpoint**: `PATCH /api/v1/public/submissions/{submission_id}/messages/{message_id}`
* **Headers**: `Content-Type: application/json`
* **JSON Body**:
```json
{
  "message": "Updated message text"
}
```

#### D. Delete Message
* **Endpoint**: `DELETE /api/v1/public/submissions/{submission_id}/messages/{message_id}`

#### E. Mark Messages as Read
* **Endpoint**: `PATCH /api/v1/public/submissions/{submission_id}/messages/read`
* **Description**: Call this when the client opens the chat window or scrolls to the bottom to mark all staff messages in the conversation as read.

---

## 👑 Admin / Staff Side Integration

### 1. Connecting the WebSocket

Establish a connection to the following URL:

```
WS_URL = ws://<backend-host>/api/v1/admin/submissions/{submission_id}/ws?token={jwt_token}
```

- **`submission_id`**: The ID of the submission conversation to monitor.
- **`jwt_token`**: The admin's standard JWT access token (stored in cookies or local storage).

---

### 2. Admin REST Endpoints

All admin requests require `Authorization: Bearer <jwt_token>` in the headers.

#### A. Fetch Message History
* **Endpoint**: `GET /api/v1/admin/submissions/{submission_id}/messages`

#### B. Send Message
* **Endpoint**: `POST /api/v1/admin/submissions/{submission_id}/messages`
* **Headers**: `Content-Type: multipart/form-data`
* **Form Data**:
  - `message` (string, optional)
  - `files` (file, optional, multiple)

#### C. Edit Staff Message
* **Endpoint**: `PATCH /api/v1/admin/submissions/{submission_id}/messages/{message_id}`
* **Headers**: `Content-Type: application/json`
* **JSON Body**:
```json
{
  "message": "Updated admin message"
}
```

#### D. Delete Message (Moderation)
* **Endpoint**: `DELETE /api/v1/admin/submissions/{submission_id}/messages/{message_id}`
* **Description**: Allows staff to delete any message in the conversation.

#### E. Mark Messages as Read
* **Endpoint**: `PATCH /api/v1/admin/submissions/{submission_id}/messages/read`
* **Description**: Marks all client messages as read.

---

## 📡 WebSocket Event Protocol

All communication over the WebSocket channel follows standard JSON structures.

### 1. Client-to-Server Messages (Sent by Frontend)

#### A. Ping Keep-Alive
To prevent network load balancers or proxy servers (like Nginx) from dropping idle connections, send a ping every 30–60 seconds:
```json
{
  "type": "ping"
}
```
*Response from Server:*
```json
{
  "type": "pong"
}
```

#### B. Typing Indicator
Send this frame when the user is actively typing in the chat input. debounce this event to avoid flooding the socket:
```json
{
  "type": "typing",
  "is_typing": true
}
```
When they stop typing, send:
```json
{
  "type": "typing",
  "is_typing": false
}
```

---

### 2. Server-to-Client Messages (Received by Frontend)

All events sent by the server have the structure:
```json
{
  "event": "event_name",
  "data": { ... }
}
```

#### A. `new_message`
Triggered when a client or staff member sends a message.
```json
{
  "event": "new_message",
  "data": {
    "id": "msg-uuid",
    "sender_type": "client" | "staff",
    "sender_name": "You" | "John Doe (Staff)",
    "message": "Message content",
    "attachments": [],
    "is_read": false,
    "created_at": "2026-08-23T20:30:54Z",
    "updated_at": "2026-08-23T20:30:54Z"
  }
}
```

#### B. `message_updated`
Triggered when a message is edited.
```json
{
  "event": "message_updated",
  "data": {
    "id": "msg-uuid",
    "message": "Updated message content",
    "updated_at": "2026-08-23T20:35:10Z"
  }
}
```

#### C. `message_deleted`
Triggered when a message is deleted.
```json
{
  "event": "message_deleted",
  "data": {
    "id": "msg-uuid"
  }
}
```

#### D. `read_receipt`
Triggered when the other participant marks the messages as read.
```json
{
  "event": "read_receipt",
  "data": {
    "read_by": "client" | "staff",
    "read_by_name": "Sarah Ade" (only present if read_by is staff),
    "read_at": "2026-08-23T20:36:00Z",
    "messages_marked": 2
  }
}
```

#### E. `typing`
Triggered when the other user starts or stops typing.
```json
{
  "event": "typing",
  "data": {
    "sender_type": "client" | "staff",
    "sender_name": "Client Name" | "Sarah Ade",
    "is_typing": true
  }
}
```

#### F. `submission_status_changed`
Triggered when the status of the submission is updated by staff.
```json
{
  "event": "submission_status_changed",
  "data": {
    "submission_id": "sub-uuid",
    "old_status": "in_progress",
    "new_status": "completed",
    "changed_by": "Sarah Ade"
  }
}
```

#### G. `submission_assigned`
Triggered when a staff member is assigned or unassigned.
```json
{
  "event": "submission_assigned",
  "data": {
    "submission_id": "sub-uuid",
    "assigned_to": {
      "id": "staff-uuid",
      "name": "Sarah Ade",
      "role": "sub_admin"
    } // will be null if unassigned
  }
}
```

---

## 🛠️ Connection Close Codes

| Close Code | Description | Recommended UI State |
|---|---|---|
| `4001` | **Authentication Failed**: Invalid or missing token | Redirect to login / show access denied. Do not retry. |
| `1006` / `1011` | **Connection Lost**: Network drop or server restart | Attempt reconnection using exponential backoff. |

---

## ⚛️ React Integration Checklist & Tips

1. **Keep-Alives**: Make sure to implement a `setInterval` pinging the server with `{"type": "ping"}` every 45 seconds to keep the socket connection alive when idle.
2. **Reconnection**: Implement a reconnection handler with exponential backoff (e.g. retry after 1s, 2s, 5s, 10s up to a cap) when closed with codes other than `4001`.
3. **Optimistic Updates**: When the user sends a message, you can optionally show it optimistically in the UI with a "sending" state. When the REST API resolves, confirm it. The WebSocket event `new_message` for the user's *own* sent messages can either be ignored by matching the `id` or verified.
4. **Typing Indicators**: Use a debounce hook (e.g. 1.5 seconds) on your message input. Send `{"type": "typing", "is_typing": true}` on keydown, and `{"type": "typing", "is_typing": false}` after 1.5 seconds of silence.
5. **Page Visibility**: Close the WebSocket when the tab goes to the background (`document.visibilityState === 'hidden'`) and reopen it when returning to the tab to save user bandwidth and battery.
