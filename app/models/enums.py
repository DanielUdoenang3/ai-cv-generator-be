from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SUB_ADMIN = "sub_admin"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class SubmissionStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING_CLIENT_INPUT = "pending_client_input"
    AI_GENERATED = "ai_generated"
    REVIEW = "review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class MessageSenderType(str, Enum):
    CLIENT = "client"
    STAFF = "staff"
    SYSTEM = "system"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    LATEX = "latex"


class AiGenerationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"



