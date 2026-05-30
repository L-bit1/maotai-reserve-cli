from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mobile: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(32), default="")
    token_enc: Mapped[str] = mapped_column(Text, default="")
    device_id: Mapped[str] = mapped_column(String(64), default="")
    province: Mapped[str] = mapped_column(String(32), default="")
    city: Mapped[str] = mapped_column(String(32), default="")
    lat: Mapped[str] = mapped_column(String(24), default="")
    lng: Mapped[str] = mapped_column(String(24), default="")
    receiver_name: Mapped[str] = mapped_column(String(64), default="")
    receiver_mobile: Mapped[str] = mapped_column(String(11), default="")
    district: Mapped[str] = mapped_column(String(64), default="")
    detail_address: Mapped[str] = mapped_column(String(256), default="")
    shop_strategy: Mapped[str] = mapped_column(String(32), default="")
    shop_id: Mapped[str] = mapped_column(String(32), default="")
    egress_group: Mapped[str] = mapped_column(String(32), default="")
    proxy_url: Mapped[str] = mapped_column(String(256), default="")
    device_ua: Mapped[str] = mapped_column(String(128), default="")
    device_mt_info: Mapped[str] = mapped_column(String(64), default="")
    device_network: Mapped[str] = mapped_column(String(16), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    end_date: Mapped[str] = mapped_column(String(8), default="99991231")
    remark: Mapped[str] = mapped_column(String(256), default="")
    last_error: Mapped[str] = mapped_column(String(512), default="")
    last_reserved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    records: Mapped[list["ReserveRecord"]] = relationship(back_populates="account")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    job_type: Mapped[str] = mapped_column(String(32), default="manual")
    cron: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    account_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    product_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    log_text: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReserveRecord(Base):
    __tablename__ = "reserve_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"))
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    item_code: Mapped[str] = mapped_column(String(16), default="")
    item_name: Mapped[str] = mapped_column(String(128), default="")
    shop_id: Mapped[str] = mapped_column(String(32), default="")
    shop_name: Mapped[str] = mapped_column(String(128), default="")
    session_id: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="failed")
    http_code: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    reserved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="records")


class LotteryResult(Base):
    __tablename__ = "lottery_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), index=True)
    mobile: Mapped[str] = mapped_column(String(11), default="")
    item_id: Mapped[str] = mapped_column(String(16), default="")
    item_name: Mapped[str] = mapped_column(String(128), default="")
    session_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="waiting")
    payment_status: Mapped[str] = mapped_column(String(16), default="none")
    order_id: Mapped[str] = mapped_column(String(64), default="")
    pay_deadline: Mapped[str] = mapped_column(String(32), default="")
    reservation_time: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(String(256), default="")
    queried_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_marked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
