"""user auth table finalise

Revision ID: d761347b2c16
Revises: c120b958ffba
Create Date: 2025-03-06 15:18:27.088220

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd761347b2c16'
down_revision = 'c120b958ffba'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_authenticate', schema=None) as batch_op:
        batch_op.alter_column('password_hashed',
               existing_type=postgresql.BYTEA(),
               type_=sa.String(),
               existing_nullable=False)
        batch_op.alter_column('salt',
               existing_type=postgresql.BYTEA(),
               type_=sa.String(),
               existing_nullable=False)
        batch_op.drop_column('hashing_algorithm')
        batch_op.drop_column('auth_id')
        batch_op.drop_column('created')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_authenticate', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('auth_id', sa.UUID(), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('hashing_algorithm', sa.VARCHAR(length=50), autoincrement=False, nullable=False))
        batch_op.alter_column('salt',
               existing_type=sa.String(),
               type_=postgresql.BYTEA(),
               existing_nullable=False)
        batch_op.alter_column('password_hashed',
               existing_type=sa.String(),
               type_=postgresql.BYTEA(),
               existing_nullable=False)

    # ### end Alembic commands ###
