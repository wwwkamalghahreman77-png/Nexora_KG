"""
منطق ارجاع لید به شرکت‌های عضو.
اولویت‌بندی: pro/enterprise قبل از free، سپس شرکت‌هایی که برای همین مسیر
داده ثبت کرده‌اند (چون تخصص/حضور در آن مسیر را ثابت کرده‌اند).
"""
from typing import List
from sqlalchemy.orm import Session
from database.models import Partner, TariffDataPoint

TIER_PRIORITY = {"enterprise": 0, "pro": 1, "free": 2}


def find_matching_partners(
    db: Session, origin_code: str, dest_code: str, limit: int = 3
) -> List[Partner]:

    verified_partners = (
        db.query(Partner)
        .filter(Partner.verified.is_(True))
        .all()
    )

    # شرکت‌هایی که برای این مسیر داده ثبت کرده‌اند
    route_partner_ids = {
        row.partner_id
        for row in db.query(TariffDataPoint.partner_id)
        .filter(
            TariffDataPoint.origin_code == origin_code,
            TariffDataPoint.dest_code == dest_code,
        )
        .distinct()
    }

    def sort_key(p: Partner):
        has_route_data = 0 if p.id in route_partner_ids else 1
        return (TIER_PRIORITY.get(p.tier, 3), has_route_data, -p.data_points_contributed)

    ranked = sorted(verified_partners, key=sort_key)
    return ranked[:limit]


def consume_lead_credit(db: Session, partner: Partner) -> bool:
    """
    پلن free فقط تعداد محدودی لید در ماه رایگان می‌گیرد؛ بعد از اتمام باید
    مشترک pro شود. این تابع اعتبار را کم می‌کند و اگر تمام شده False برمی‌گرداند.
    """
    if partner.tier != "free":
        return True  # اشتراک‌های پولی محدودیت لید ندارند

    if partner.lead_credits > 0:
        partner.lead_credits -= 1
        db.commit()
        return True

    return False
