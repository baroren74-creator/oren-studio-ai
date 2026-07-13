"""add projects.source_text

Revision ID: c8f2a1d4b6e7
Revises: b7e3f0a5c1d9
Create Date: 2026-07-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c8f2a1d4b6e7'
down_revision = 'b7e3f0a5c1d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('source_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'source_text')
