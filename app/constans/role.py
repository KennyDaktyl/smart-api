import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLIENT = "client"
    CLIENT_PRO = "client_pro"
    DEMO = "demo"
