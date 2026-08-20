from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SUB_ADMIN = "sub_admin"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


# class Status(str, Enum):
#     PENDING = "pending"
#     APPROVED = "approved"
#     REJECTED = "rejected"


