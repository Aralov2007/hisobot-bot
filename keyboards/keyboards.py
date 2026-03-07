from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List
from database.models import Report, Material, EditRequest, User, UserStatus


# ===== CONTACT =====
def contact_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    return kb


# ===== USER MAIN MENU =====
def user_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Hisobot yuborish")],
            [KeyboardButton(text="📊 Mening statistikam")],
            [KeyboardButton(text="📋 Arizalar"), KeyboardButton(text="ℹ️ Ma'lumot")],
        ],
        resize_keyboard=True
    )
    return kb


# ===== ADMIN MAIN MENU =====
def admin_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Hisobotlar"), KeyboardButton(text="📨 Arizalar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🗂 Materiallar"), KeyboardButton(text="⚙️ Admin boshqaruv")],
        ],
        resize_keyboard=True
    )
    return kb


def super_admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Hisobotlar"), KeyboardButton(text="📨 Arizalar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🗂 Materiallar"), KeyboardButton(text="👑 Adminlar")],
        ],
        resize_keyboard=True
    )
    return kb


# ===== STATISTICS MENU =====
def stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Oxirgi hisobotlar", callback_data="stats:recent")
    builder.button(text="📆 Haftalik", callback_data="stats:weekly")
    builder.button(text="🗓 Oylik", callback_data="stats:monthly")
    builder.button(text="📦 Jami materiallar", callback_data="stats:materials")
    builder.button(text="🔙 Orqaga", callback_data="stats:back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


# ===== WORK TYPES =====
WORK_TYPES = [
    "Montaj ishlari",
    "Kabel tortish",
    "Ulash ishlari",
    "Schit montaji",
    "Test va sinovlar",
    "Ta'mirlash ishlari",
    "Boshqa"
]


def work_type_keyboard():
    builder = InlineKeyboardBuilder()
    for wt in WORK_TYPES:
        builder.button(text=wt, callback_data=f"work_type:{wt}")
    builder.button(text="✍️ Boshqa (qo'lda kiriting)", callback_data="work_type:custom")
    builder.adjust(2)
    return builder.as_markup()


# ===== MATERIALS SELECTION =====
def materials_page_keyboard(materials: List[Material], page: int = 0, page_size: int = 8):
    builder = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size
    page_materials = materials[start:end]

    for mat in page_materials:
        builder.button(
            text=f"{mat.name} ({mat.unit})",
            callback_data=f"mat_select:{mat.id}:{mat.unit}"
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"mat_page:{page-1}"))
    if end < len(materials):
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"mat_page:{page+1}"))

    builder.adjust(2)
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="✍️ Boshqa material", callback_data="mat_custom"),
        InlineKeyboardButton(text="✅ Tayyor", callback_data="mat_done")
    )
    return builder.as_markup()


def quantity_confirm_keyboard(material_name: str, unit: str):
    builder = InlineKeyboardBuilder()
    common_qtys = [1, 2, 5, 10, 20, 50, 100]
    for q in common_qtys:
        builder.button(text=f"{q} {unit}", callback_data=f"qty:{q}")
    builder.button(text="✍️ Boshqa miqdor", callback_data="qty:custom")
    builder.adjust(4)
    return builder.as_markup()


# ===== REPORT CONFIRM =====
def report_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data="report:confirm")
    builder.button(text="❌ Bekor qilish", callback_data="report:cancel")
    builder.adjust(2)
    return builder.as_markup()


def photo_skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ Rasm yuklashni o'tkazib yuborish", callback_data="photo:skip")
    builder.adjust(1)
    return builder.as_markup()


# ===== ADMIN REPORT ACTIONS =====
def admin_report_actions(report_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"admin_report:approve:{report_id}")
    builder.button(text="❌ Rad etish", callback_data=f"admin_report:reject:{report_id}")
    builder.button(text="✏️ Tahrirlash", callback_data=f"admin_report:edit:{report_id}")
    builder.button(text="🔙 Orqaga", callback_data="admin_report:list")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def admin_reports_list_keyboard(reports: List[Report], page: int = 0, page_size: int = 5):
    builder = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size
    page_reports = reports[start:end]

    for r in page_reports:
        status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(r.status.value, "❓")
        date_str = r.report_date.strftime("%d.%m")
        builder.button(
            text=f"{status_emoji} {r.user.full_name[:15]} | {date_str} | {r.work_type[:10]}",
            callback_data=f"view_report:{r.id}"
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"reports_page:{page-1}"))
    if end < len(reports):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"reports_page:{page+1}"))

    builder.adjust(1)
    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


# ===== PENDING USERS =====
def pending_user_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Faollashtirish", callback_data=f"user_approve:{user_id}")
    builder.button(text="❌ Rad etish", callback_data=f"user_reject:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def users_list_keyboard(users: List[User]):
    builder = InlineKeyboardBuilder()
    for user in users:
        status_emoji = {"active": "🟢", "pending": "🟡", "blocked": "🔴"}.get(user.status.value, "⚪")
        builder.button(
            text=f"{status_emoji} {user.full_name}",
            callback_data=f"view_user:{user.id}"
        )
    builder.adjust(1)
    return builder.as_markup()


def user_manage_keyboard(user_id: int, current_status: UserStatus):
    builder = InlineKeyboardBuilder()
    if current_status != UserStatus.ACTIVE:
        builder.button(text="✅ Faollashtirish", callback_data=f"manage_user:activate:{user_id}")
    if current_status != UserStatus.BLOCKED:
        builder.button(text="🚫 Bloklash", callback_data=f"manage_user:block:{user_id}")
    builder.button(text="🔙 Ro'yxatga qaytish", callback_data="users:list")
    builder.adjust(2, 1)
    return builder.as_markup()


# ===== EDIT REQUESTS =====
def request_actions_keyboard(request_id: int, report_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Hal qilindi", callback_data=f"req:resolve:{request_id}")
    builder.button(text="✏️ Hisobotni tahrirlash", callback_data=f"req:edit_report:{report_id}:{request_id}")
    builder.button(text="🗑 Yopish", callback_data=f"req:close:{request_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


# ===== ADMIN MANAGEMENT =====
def admin_list_keyboard(admins: List[User]):
    builder = InlineKeyboardBuilder()
    for admin in admins:
        role_emoji = "👑" if admin.role.value == "super_admin" else "🛠"
        builder.button(
            text=f"{role_emoji} {admin.full_name}",
            callback_data=f"admin_manage:{admin.id}"
        )
    builder.button(text="➕ Yangi admin qo'shish", callback_data="admin_add:new")
    builder.adjust(1)
    return builder.as_markup()


def admin_permissions_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔓 To'liq huquq", callback_data=f"set_admin_perm:{user_id}:full")
    builder.button(text="🔒 Cheklangan huquq", callback_data=f"set_admin_perm:{user_id}:limited")
    builder.button(text="❌ Adminlikdan olib tashlash", callback_data=f"remove_admin:{user_id}")
    builder.button(text="🔙 Orqaga", callback_data="admins:list")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


# ===== EXPORT =====
def export_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Excel", callback_data="export:excel")
    builder.button(text="📄 PDF", callback_data="export:pdf")
    builder.adjust(2)
    return builder.as_markup()


def remove_keyboard():
    return ReplyKeyboardRemove()
