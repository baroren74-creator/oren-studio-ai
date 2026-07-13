"""add prompt_library table

Revision ID: 9d2c4a7e1f6b
Revises: f4b1e6c8a9d3
Create Date: 2026-07-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '9d2c4a7e1f6b'
down_revision = 'f4b1e6c8a9d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('prompt_library',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=True),
    sa.Column('prompt_text', sa.Text(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['prompt_library.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('prompt_library')
