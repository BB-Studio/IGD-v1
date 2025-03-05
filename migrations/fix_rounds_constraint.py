
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Drop the NOT NULL constraint on the rounds column
    op.alter_column('tournament', 'rounds', nullable=True, existing_type=sa.Integer())

def downgrade():
    # Add back the NOT NULL constraint if needed
    op.alter_column('tournament', 'rounds', nullable=False, existing_type=sa.Integer())
