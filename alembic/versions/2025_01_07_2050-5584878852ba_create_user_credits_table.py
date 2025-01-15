"""create user_credits table

Revision ID: 5584878852ba
Revises: 6cc80b195fc9
Create Date: 2025-01-07 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '5584878852ba'
down_revision = '6cc80b195fc9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('user_credits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('remaining_analyses', sa.Integer(), default=0),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_credits_id'), 'user_credits', ['id'], unique=False)
    op.create_index(op.f('ix_user_credits_user_id'), 'user_credits', ['user_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_user_credits_user_id'), table_name='user_credits')
    op.drop_index(op.f('ix_user_credits_id'), table_name='user_credits')
    op.drop_table('user_credits')