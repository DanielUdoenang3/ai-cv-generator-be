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
    COMPLETED = "completed"
    REJECTED = "rejected"


class MessageSenderType(str, Enum):
    CLIENT = "client"
    STAFF = "staff"
    SYSTEM = "system"



# class Status(str, Enum):
#     PENDING = "pending"
#     APPROVED = "approved"
#     REJECTED = "rejected"


