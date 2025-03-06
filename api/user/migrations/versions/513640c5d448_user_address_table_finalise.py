"""user address table finalise

Revision ID: 513640c5d448
Revises: d761347b2c16
Create Date: 2025-03-06 16:23:10.881874

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '513640c5d448'
down_revision = 'd761347b2c16'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_address', schema=None) as batch_op:
        batch_op.drop_column('address_id')
        batch_op.drop_column('created')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_address', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('address_id', sa.UUID(), autoincrement=False, nullable=False))

    # ### end Alembic commands ###
