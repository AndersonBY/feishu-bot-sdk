from enum import Enum


class MemberIdType(str, Enum):
    OPEN_ID = "open_id"
    USER_ID = "user_id"
    UNION_ID = "union_id"


class Permission(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    FULL_ACCESS = "full_access"


class DriveResourceType(str, Enum):
    BITABLE = "bitable"
    DOCX = "docx"
