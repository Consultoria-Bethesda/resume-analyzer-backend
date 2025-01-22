"""add email verification columns

Revision ID: add_email_verification
Create Date: 2024-01-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Add all required columns
    op.add_column('users', sa.Column('email_verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reset_password_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_password_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))

def downgrade() -> None:
    # Remove all added columns
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'reset_password_token')
    op.drop_column('users', 'reset_password_expires')
    op.drop_column('users', 'stripe_customer_id')