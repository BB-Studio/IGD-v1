
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add rounds_count column to tournament table
    op.add_column('tournament', sa.Column('rounds_count', sa.Integer(), nullable=True, default=0))
    
    # Set rounds_count to 0 for existing tournaments
    op.execute("UPDATE tournament SET rounds_count = 0")
    
    # Drop the NOT NULL constraint on the rounds column if it exists
    try:
        op.alter_column('tournament', 'rounds', nullable=True, existing_type=sa.Integer())
    except:
        pass  # Column might not exist or already be nullable

def downgrade():
    # Remove rounds_count column
    op.drop_column('tournament', 'rounds_count')
    
    # Add back the NOT NULL constraint if needed
    try:
        op.alter_column('tournament', 'rounds', nullable=False, existing_type=sa.Integer())
    except:
        pass  # Column might not exist
