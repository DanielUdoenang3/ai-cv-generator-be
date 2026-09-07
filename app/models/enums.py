from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SUB_ADMIN = "sub_admin"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    OTHER = "other"


class SexualOrientation(str, Enum):
    HETEROSEXUAL = "heterosexual"
    GAY_OR_LESBIAN = "gay_or_lesbian"
    BISEXUAL = "bisexual"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    OTHER = "other"


class RaceEthnicity(str, Enum):
    AMERICAN_INDIAN_OR_ALASKA_NATIVE = "american_indian_or_alaska_native"
    ASIAN = "asian"
    BLACK_OR_AFRICAN_AMERICAN = "black_or_african_american"
    HISPANIC_OR_LATINO = "hispanic_or_latino"
    NATIVE_HAWAIIAN_OR_PACIFIC_ISLANDER = "native_hawaiian_or_pacific_islander"
    WHITE = "white"
    TWO_OR_MORE_RACES = "two_or_more_races"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    OTHER = "other"


class VeteranStatus(str, Enum):
    NOT_A_VETERAN = "not_a_veteran"
    VETERAN = "veteran"
    ACTIVE_DUTY = "active_duty"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class WorkArrangement(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FLEXIBLE = "flexible"


class VisaSponsorship(str, Enum):
    YES = "yes"
    NO = "no"
    NOT_APPLICABLE = "not_applicable"


class SecurityClearance(str, Enum):
    NONE = "none"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    TOP_SECRET_SCI = "top_secret_sci"
    OTHER = "other"


class DisabilityStatus(str, Enum):
    YES = "yes"
    NO = "no"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


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
