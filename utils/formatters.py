from database.models import Report, ReportStatus
from datetime import datetime
from typing import Dict


STATUS_EMOJI = {
    "pending": "⏳",
    "approved": "✅",
    "rejected": "❌"
}


def format_report(report: Report, show_user: bool = False, detailed: bool = False) -> str:
    status_emoji = STATUS_EMOJI.get(report.status.value, "❓")
    date_str = report.report_date.strftime("%d.%m.%Y %H:%M")

    lines = []
    if show_user and report.user:
        lines.append(f"👤 {report.user.full_name}")
    lines.append(f"📅 {date_str}")
    lines.append(f"📌 Ish turi: {report.work_type}")
    lines.append(f"📊 Holat: {status_emoji} {report.status.value.upper()}")

    if report.materials:
        lines.append("📦 Materiallar:")
        for rm in report.materials:
            name = rm.material.name if rm.material else rm.custom_name or "Noma'lum"
            lines.append(f"  • {name}: {rm.quantity} {rm.unit}")

    if report.note:
        lines.append(f"💬 Izoh: {report.note}")

    if report.photo_path:
        lines.append("📸 Rasm: ✅")

    if detailed and report.admin_comment:
        lines.append(f"🔔 Admin izohi: {report.admin_comment}")

    return "\n".join(lines)


def format_materials_stats(stats: Dict, title: str = "📦 Material statistikasi") -> str:
    if not stats:
        return f"{title}\n\n📭 Ma'lumot yo'q."

    lines = [title, ""]
    total_items = len(stats)

    # Sort by total desc
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)

    for name, data in sorted_stats:
        qty = data["total"]
        unit = data["unit"]
        # Format quantity
        if qty == int(qty):
            qty_str = str(int(qty))
        else:
            qty_str = f"{qty:.1f}"
        lines.append(f"• {name}: {qty_str} {unit}")

    lines.append(f"\n📊 Jami: {total_items} xil material")
    return "\n".join(lines)


def format_date_range(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}"
