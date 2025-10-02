"""Initial DB baseline

Revision ID: 0001_baseline
Revises: 
Create Date: 2025-09-26 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=255), nullable=True, unique=True, index=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    op.create_table(
        'calls',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('call_id', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('phone_number', sa.String(length=20), nullable=False, index=True),
        sa.Column('caller_id', sa.String(length=50), nullable=False, server_default=sa.text("'Outbound Call'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('context', sa.String(length=50), nullable=False, server_default=sa.text("'outbound-ivr'")),
        sa.Column('extension', sa.String(length=50), nullable=False, server_default=sa.text("'s'")),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('timeout', sa.Integer(), nullable=False, server_default=sa.text('30000')),
        sa.Column('channel', sa.String(length=255), nullable=True),
        sa.Column('unique_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('dialed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('billable_duration', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('call_metadata', sa.Text(), nullable=True),
    )
    # Indexes & constraints matching model definitions
    op.create_index('ix_calls_created_at', 'calls', ['created_at'])
    op.create_index('ix_calls_status_created', 'calls', ['status', 'created_at'])
    op.create_index('ix_calls_unique_id', 'calls', ['unique_id'])
    # Check constraints (implemented via triggers or app-level logic if dialect lacks direct support)
    # For portability, enforce via application; optionally add partial constraints with dialect-specific DDL.


def downgrade() -> None:
    op.drop_table('calls')
    op.drop_table('users')
