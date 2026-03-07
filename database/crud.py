from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
from typing import Optional, List
from database.models import (
    User, Report, ReportMaterial, Material,
    EditRequest, ActivityLog, UserRole, UserStatus,
    ReportStatus, RequestStatus, AdminPermission
)
import logging

logger = logging.getLogger(__name__)


# ===== USER CRUD =====

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, full_name: str,
                      phone: str = None, username: str = None) -> User:
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        phone=phone,
        username=username,
        role=UserRole.USER,
        status=UserStatus.PENDING
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_users(session: AsyncSession, status: UserStatus = None) -> List[User]:
    query = select(User)
    if status:
        query = query.where(User.status == status)
    result = await session.execute(query.order_by(User.created_at.desc()))
    return result.scalars().all()


async def update_user_status(session: AsyncSession, user_id: int, status: UserStatus) -> bool:
    await session.execute(
        update(User).where(User.id == user_id).values(status=status)
    )
    await session.commit()
    return True


async def get_all_admins(session: AsyncSession) -> List[User]:
    result = await session.execute(
        select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
    )
    return result.scalars().all()


async def set_user_role(session: AsyncSession, user_id: int, role: UserRole,
                        permission: AdminPermission = None) -> bool:
    await session.execute(
        update(User).where(User.id == user_id).values(role=role, admin_permission=permission)
    )
    await session.commit()
    return True


# ===== REPORT CRUD =====

async def has_report_today(session: AsyncSession, user_id: int) -> bool:
    today = date.today()
    result = await session.execute(
        select(Report).where(
            and_(
                Report.user_id == user_id,
                func.date(Report.report_date) == today
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def create_report(session: AsyncSession, user_id: int, work_type: str,
                        note: str = None, photo_path: str = None) -> Report:
    report = Report(
        user_id=user_id,
        work_type=work_type,
        note=note,
        photo_path=photo_path,
        status=ReportStatus.PENDING
    )
    session.add(report)
    await session.flush()
    return report


async def add_report_material(session: AsyncSession, report_id: int,
                               material_id: int = None, custom_name: str = None,
                               quantity: float = 1.0, unit: str = "dona") -> ReportMaterial:
    rm = ReportMaterial(
        report_id=report_id,
        material_id=material_id,
        custom_name=custom_name,
        quantity=quantity,
        unit=unit
    )
    session.add(rm)
    return rm


async def get_reports_by_user(session: AsyncSession, user_id: int,
                               limit: int = 10, offset: int = 0) -> List[Report]:
    result = await session.execute(
        select(Report)
        .options(selectinload(Report.materials).selectinload(ReportMaterial.material))
        .where(Report.user_id == user_id)
        .order_by(Report.report_date.desc())
        .limit(limit).offset(offset)
    )
    return result.scalars().all()


async def get_report_by_id(session: AsyncSession, report_id: int) -> Optional[Report]:
    result = await session.execute(
        select(Report)
        .options(
            selectinload(Report.materials).selectinload(ReportMaterial.material),
            selectinload(Report.user)
        )
        .where(Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_all_reports(session: AsyncSession, status: ReportStatus = None,
                           limit: int = 20, offset: int = 0) -> List[Report]:
    query = select(Report).options(
        selectinload(Report.user),
        selectinload(Report.materials).selectinload(ReportMaterial.material)
    )
    if status:
        query = query.where(Report.status == status)
    query = query.order_by(Report.report_date.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def update_report_status(session: AsyncSession, report_id: int,
                                status: ReportStatus, admin_comment: str = None) -> bool:
    values = {"status": status}
    if admin_comment:
        values["admin_comment"] = admin_comment
    await session.execute(update(Report).where(Report.id == report_id).values(**values))
    await session.commit()
    return True


async def get_weekly_reports(session: AsyncSession, user_id: int) -> List[Report]:
    week_ago = datetime.now() - timedelta(days=7)
    result = await session.execute(
        select(Report)
        .options(selectinload(Report.materials).selectinload(ReportMaterial.material))
        .where(and_(Report.user_id == user_id, Report.report_date >= week_ago))
        .order_by(Report.report_date.desc())
    )
    return result.scalars().all()


async def get_monthly_reports(session: AsyncSession, user_id: int = None,
                               year: int = None, month: int = None) -> List[Report]:
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    query = select(Report).options(
        selectinload(Report.user),
        selectinload(Report.materials).selectinload(ReportMaterial.material)
    ).where(
        and_(
            extract("year", Report.report_date) == year,
            extract("month", Report.report_date) == month
        )
    )
    if user_id:
        query = query.where(Report.user_id == user_id)

    result = await session.execute(query.order_by(Report.report_date.desc()))
    return result.scalars().all()


async def get_users_without_report_today(session: AsyncSession) -> List[User]:
    today = date.today()
    subquery = select(Report.user_id).where(func.date(Report.report_date) == today)
    result = await session.execute(
        select(User).where(
            and_(
                User.status == UserStatus.ACTIVE,
                User.role == UserRole.USER,
                ~User.id.in_(subquery)
            )
        )
    )
    return result.scalars().all()


# ===== MATERIALS CATALOG =====

async def get_all_materials(session: AsyncSession) -> List[Material]:
    result = await session.execute(
        select(Material).where(Material.is_active == True).order_by(Material.category, Material.name)
    )
    return result.scalars().all()


async def get_material_by_id(session: AsyncSession, material_id: int) -> Optional[Material]:
    result = await session.execute(select(Material).where(Material.id == material_id))
    return result.scalar_one_or_none()


async def create_material(session: AsyncSession, name: str, unit: str, category: str) -> Material:
    mat = Material(name=name, unit=unit, category=category)
    session.add(mat)
    await session.commit()
    await session.refresh(mat)
    return mat


# ===== EDIT REQUESTS =====

async def create_edit_request(session: AsyncSession, user_id: int,
                               report_id: int, reason: str) -> EditRequest:
    req = EditRequest(user_id=user_id, report_id=report_id, reason=reason)
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def get_open_requests(session: AsyncSession) -> List[EditRequest]:
    result = await session.execute(
        select(EditRequest)
        .options(selectinload(EditRequest.user), selectinload(EditRequest.report))
        .where(EditRequest.status == RequestStatus.OPEN)
        .order_by(EditRequest.created_at.desc())
    )
    return result.scalars().all()


async def resolve_request(session: AsyncSession, request_id: int,
                           admin_response: str = None) -> bool:
    await session.execute(
        update(EditRequest).where(EditRequest.id == request_id).values(
            status=RequestStatus.RESOLVED,
            admin_response=admin_response,
            resolved_at=func.now()
        )
    )
    await session.commit()
    return True


# ===== ACTIVITY LOG =====

async def log_activity(session: AsyncSession, user_id: int, action: str, details: dict = None):
    log = ActivityLog(user_id=user_id, action=action, details=details)
    session.add(log)
    await session.commit()


# ===== STATISTICS =====

async def get_material_stats(session: AsyncSession, user_id: int = None,
                              year: int = None, month: int = None) -> dict:
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    query = select(
        ReportMaterial.custom_name,
        Material.name,
        Material.unit,
        func.sum(ReportMaterial.quantity).label("total")
    ).join(Report, ReportMaterial.report_id == Report.id
    ).outerjoin(Material, ReportMaterial.material_id == Material.id
    ).where(
        and_(
            extract("year", Report.report_date) == year,
            extract("month", Report.report_date) == month
        )
    )

    if user_id:
        query = query.where(Report.user_id == user_id)

    query = query.group_by(ReportMaterial.custom_name, Material.name, Material.unit)
    result = await session.execute(query)
    rows = result.fetchall()

    stats = {}
    for row in rows:
        name = row.name or row.custom_name or "Noma'lum"
        unit = row.unit or "dona"
        stats[name] = {"total": float(row.total), "unit": unit}
    return stats
