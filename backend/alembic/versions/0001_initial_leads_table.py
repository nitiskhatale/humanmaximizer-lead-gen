"""Initial leads table

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("lead_uuid", sa.String(36), nullable=False, unique=True, index=True),
        # Search context
        sa.Column("keyword", sa.String(500), nullable=False, server_default=""),
        sa.Column("location", sa.String(200), nullable=False, server_default=""),
        # Company info
        sa.Column("company_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("domain", sa.String(500), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("industry", sa.String(200), nullable=False, server_default=""),
        sa.Column("hq_location", sa.String(200), nullable=False, server_default=""),
        sa.Column("tech_stack_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("decision_makers_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("raw_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("growth_signal", sa.String(50), nullable=False, server_default="unknown"),
        # Qualification
        sa.Column("qualification_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("score_breakdown_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("qualification_reasoning", sa.Text, nullable=False, server_default=""),
        sa.Column("is_qualified", sa.Boolean, nullable=False, server_default="0"),
        # Outreach
        sa.Column("outreach_email_json", sa.Text, nullable=True),
        sa.Column("linkedin_message", sa.Text, nullable=True),
        sa.Column("rag_context_json", sa.Text, nullable=False, server_default="[]"),
        # Metadata
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("errors_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("processing_time_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("leads")
