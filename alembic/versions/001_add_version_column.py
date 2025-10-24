"""Add version column for optimistic locking

Revision ID: add_version_column
Revises: 
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_version_column'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add version column with default value 0
    op.add_column('calls', sa.Column('version', sa.Integer(), nullable=False, server_default='0'))
    
    # Create index on version for faster queries
    op.create_index('ix_calls_version', 'calls', ['version'], unique=False)


def downgrade():
    # Drop index first
    op.drop_index('ix_calls_version', table_name='calls')
    
    # Drop column
    op.drop_column('calls', 'version')
