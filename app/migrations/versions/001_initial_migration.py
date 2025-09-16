from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create carrier_users table
    op.create_table('tfst_carrier_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salesforce_user_id', sa.String(255), nullable=False),
        sa.Column('carrier_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('can_update_shipments', sa.Boolean(), nullable=False, default=True),
        sa.Column('can_upload_documents', sa.Boolean(), nullable=False, default=True),
        sa.Column('can_view_analytics', sa.Boolean(), nullable=False, default=False),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('salesforce_user_id'),
        sa.UniqueConstraint('email')
    )
    
    # Create user_sessions table
    op.create_table('tfst_user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['tfst_carrier_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    
    # Create s3_upload_logs table
    op.create_table('tfst_s3_upload_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('carrier_id', sa.String(255), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('s3_key', sa.String(500), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=False, default=0),
        sa.Column('records_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('tfst_s3_upload_logs')
    op.drop_table('tfst_user_sessions')
    op.drop_table('tfst_carrier_users')