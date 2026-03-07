from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean, DateTime, Float,
    Text, ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RequestStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AdminPermission(str, enum.Enum):
    FULL = "full"
    LIMITED = "limited"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    username = Column(String(100), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.PENDING, nullable=False)
    admin_permission = Column(SAEnum(AdminPermission), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    requests = relationship("EditRequest", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.full_name} ({self.role})>"


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False, default="dona")
    category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report_materials = relationship("ReportMaterial", back_populates="material")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    work_type = Column(String(255), nullable=False)
    report_date = Column(DateTime(timezone=True), server_default=func.now())
    note = Column(Text, nullable=True)
    status = Column(SAEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    admin_comment = Column(Text, nullable=True)
    photo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="reports")
    materials = relationship("ReportMaterial", back_populates="report", cascade="all, delete-orphan")
    edit_requests = relationship("EditRequest", back_populates="report")


class ReportMaterial(Base):
    __tablename__ = "report_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    custom_name = Column(String(255), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    report = relationship("Report", back_populates="materials")
    material = relationship("Material", back_populates="report_materials")


class EditRequest(Base):
    __tablename__ = "edit_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SAEnum(RequestStatus), default=RequestStatus.OPEN, nullable=False)
    admin_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="requests")
    report = relationship("Report", back_populates="edit_requests")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="logs")
