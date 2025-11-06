import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLIENT = "client"
    DEMO = "demo"
