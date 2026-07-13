"""add storyboards table

Revision ID: b7e3f0a5c1d9
Revises: 9d2c4a7e1f6b
Create Date: 2026-07-13 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e3f0a5c1d9'
down_revision = '9d2c4a7e1f6b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('storyboards',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('script_id', sa.String(length=36), nullable=False),
    sa.Column('scenes', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('storyboards')
