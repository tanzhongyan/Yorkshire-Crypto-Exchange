"""Add token_id and currency_code to FiatToCrypto transactions

Revision ID: c13d9eefff62
Revises: c5757f533cd9
Create Date: 2025-04-03 14:05:37.970205

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c13d9eefff62'
down_revision = 'c5757f533cd9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transaction_fiat_to_crypto', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token_id', sa.String(length=15), nullable=False))
        batch_op.add_column(sa.Column('currency_code', sa.String(length=3), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transaction_fiat_to_crypto', schema=None) as batch_op:
        batch_op.drop_column('currency_code')
        batch_op.drop_column('token_id')

    # ### end Alembic commands ###
