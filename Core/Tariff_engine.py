"""
موتور تخمین تعرفه.

منطق:
1. دقیق‌ترین حالت: رکوردهای دقیقاً همون مسیر + کالا + نوع واگن را پیدا کن،
   میانگین بگیر (نرخ به تناژ درخواستی مقیاس‌بندی می‌شود).
2. اگر رکورد دقیق نبود: همون مسیر (مبدا-مقصد) با هر نوع کالا/واگن -> میانگین
   با ضریب عدم‌قطعیت پایین‌تر (به کاربر گفته می‌شود "تخمین تقریبی").
3. اگر اصلاً داده‌ای برای این مسیر نبود: خروجی "داده کافی نیست" +
   دعوت از شرکت‌های عضو برای ثبت این مسیر (تا در آینده اولویت لید بگیرند).

هرچه شرکت‌های بیشتری داده وارد کنند، دقت بات بالاتر می‌رود - این خودِ
انگیزه‌ی مشارکت شرکت‌هاست (فلای‌ویل داده).
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import and_
from sqlalchemy.orm import Session
from database.models import TariffDataPoint


@dataclass
class TariffEstimate:
    found: bool
    confidence: str            # "high" | "medium" | "low" | "none"
    price_usd: Optional[float]
    sample_size: int
    message: str


def _normalize_price(dp: TariffDataPoint, target_weight: float) -> float:
    """همه رکوردها را به کرایه کل برای وزن درخواستی تبدیل می‌کند"""
    if dp.price_unit == "per_ton":
        return dp.price_usd * target_weight
    # اگر total بود، بر اساس نسبت وزن مقیاس می‌کنیم (تخمین خطی ساده)
    if dp.weight_tons <= 0:
        return dp.price_usd
    return dp.price_usd * (target_weight / dp.weight_tons)


def estimate_tariff(
    db: Session,
    origin_code: str,
    dest_code: str,
    cargo_code: str,
    wagon_type: str,
    weight_tons: float,
) -> TariffEstimate:

    base_query = db.query(TariffDataPoint).filter(
        and_(
            TariffDataPoint.origin_code == origin_code,
            TariffDataPoint.dest_code == dest_code,
        )
    )

    # سطح ۱: تطابق کامل
    exact = base_query.filter(
        and_(
            TariffDataPoint.cargo_code == cargo_code,
            TariffDataPoint.wagon_type == wagon_type,
        )
    ).all()

    if exact:
        prices = [_normalize_price(dp, weight_tons) for dp in exact]
        avg = sum(prices) / len(prices)
        return TariffEstimate(
            found=True,
            confidence="high" if len(exact) >= 3 else "medium",
            price_usd=round(avg, 2),
            sample_size=len(exact),
            message=f"بر اساس {len(exact)} نمونه واقعی همین مسیر و نوع بار.",
        )

    # سطح ۲: همون مسیر، هر کالا/واگن
    route_only = base_query.all()
    if route_only:
        prices = [_normalize_price(dp, weight_tons) for dp in route_only]
        avg = sum(prices) / len(prices)
        return TariffEstimate(
            found=True,
            confidence="low",
            price_usd=round(avg, 2),
            sample_size=len(route_only),
            message=(
                f"داده دقیق برای این نوع کالا/واگن نداریم؛ تخمین بر اساس "
                f"{len(route_only)} نمونه مشابه در همین مسیر است. "
                f"دقت بیشتر نیازمند ثبت داده توسط شرکت‌های عضو است."
            ),
        )

    # سطح ۳: هیچ داده‌ای نیست
    return TariffEstimate(
        found=False,
        confidence="none",
        price_usd=None,
        sample_size=0,
        message=(
            "هنوز داده‌ای برای این مسیر در شبکه ثبت نشده. "
            "درخواست شما به شرکت‌های عضو ارسال می‌شود تا برایتان قیمت واقعی بدهند "
            "(و با ثبت این مسیر، در جستجوهای بعدی اولویت نمایش می‌گیرند)."
        ),
    )
