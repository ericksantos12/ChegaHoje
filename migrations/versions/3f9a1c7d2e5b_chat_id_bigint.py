"""chat_id_bigint

Ids de supergrupos do Telegram (-100xxxxxxxxxx) não cabem em int4,
então encomendas.chat_id passa a ser BIGINT.

Revision ID: 3f9a1c7d2e5b
Revises: b4c28da2364a
Create Date: 2026-11-10 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f9a1c7d2e5b'
down_revision: Union[str, Sequence[str], None] = 'b4c28da2364a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'encomendas',
        'chat_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    Falha se existir algum chat_id fora do intervalo de int4 (ex.: supergrupos);
    remova ou migre essas linhas antes de fazer o downgrade.
    """
    op.alter_column(
        'encomendas',
        'chat_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
