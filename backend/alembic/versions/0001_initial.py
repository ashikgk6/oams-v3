"""Initial schema for OAMS."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("manager_id", sa.Integer(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_foreign_key("fk_teams_manager", "teams", "users", ["manager_id"], ["id"])

    op.create_table(
        "kiosks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("pair_code", sa.String(16), unique=True, nullable=True),
        sa.Column("secret", sa.String(64), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "display_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("token_prefix", sa.String(12), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_display_tokens_token_hash", "display_tokens", ["token_hash"], unique=True)

    op.create_table(
        "punch_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kiosk_id", sa.Integer(), sa.ForeignKey("kiosks.id"), nullable=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("nonce", sa.String(64), unique=True, nullable=True),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_punch_events_user_id", "punch_events", ["user_id"])
    op.create_index("ix_punch_events_ts", "punch_events", ["ts"])
    op.create_index("ix_punch_user_ts", "punch_events", ["user_id", "ts"])

    op.create_table(
        "attendance_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("first_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_minutes", sa.Integer(), nullable=True),
        sa.Column("late_minutes", sa.Integer(), nullable=True),
        sa.Column("finalized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )
    op.create_index("ix_attendance_days_user_id", "attendance_days", ["user_id"])
    op.create_index("ix_attendance_days_date", "attendance_days", ["date"])

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type", sa.String(32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("approver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_leave_requests_user_id", "leave_requests", ["user_id"])

    op.create_table(
        "punch_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("requested_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("approver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_punch_corrections_user_id", "punch_corrections", ["user_id"])

    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_table(
        "office_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("office_name", sa.String(200)),
        sa.Column("timezone", sa.String(64)),
        sa.Column("shift_start", sa.Time(), nullable=False),
        sa.Column("shift_end", sa.Time(), nullable=False),
        sa.Column("grace_minutes", sa.Integer()),
        sa.Column("half_day_after", sa.Time(), nullable=False),
        sa.Column("min_half_day_minutes", sa.Integer()),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "used_nonces",
        sa.Column("nonce", sa.String(64), primary_key=True),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(80), nullable=False),
        sa.Column("job_key", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.UniqueConstraint("job_name", "job_key", name="uq_job_name_key"),
    )


def downgrade() -> None:
    for table in (
        "job_runs",
        "used_nonces",
        "audit_logs",
        "office_settings",
        "holidays",
        "punch_corrections",
        "leave_requests",
        "attendance_days",
        "punch_events",
        "display_tokens",
        "kiosks",
        "users",
        "teams",
    ):
        op.drop_table(table)
