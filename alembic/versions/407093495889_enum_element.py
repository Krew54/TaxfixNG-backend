"""enum element

Revision ID: 407093495889
Revises: ddcd34bb613f
Create Date: 2025-12-17 22:48:41.541497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '407093495889'
down_revision: Union[str, None] = 'ddcd34bb613f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make file_url nullable
    op.alter_column(
        'documents',
        'file_url',
        existing_type=sa.VARCHAR(),
        nullable=True
    )

    # 2. Rename old enum
    op.execute("""
        ALTER TYPE document_category RENAME TO document_category_old;
    """)

    # 3. Create new enum with ONLY desired values
    op.execute("""
        CREATE TYPE document_category AS ENUM (
            'income',
            'other_incomes',
            'operating_expenses',
            'other_expenses',
            'life_insurance',
            'house_rent',
            'statutory_deductions'
        );
    """)

    # 4. Update column to use new enum
    op.execute("""
        ALTER TABLE documents
        ALTER COLUMN category
        TYPE document_category
        USING category::text::document_category;
    """)

    # 5. Drop old enum
    op.execute("""
        DROP TYPE document_category_old;
    """)


def downgrade() -> None:
    # Restore old enum
    op.execute("""
        CREATE TYPE document_category_old AS ENUM (
            'income',
            'other_expenses',
            'life_insurance',
            'house_rent',
            'NHF'
        );
    """)

    op.execute("""
        ALTER TABLE documents
        ALTER COLUMN category
        TYPE document_category_old
        USING category::text::document_category_old;
    """)

    op.execute("""
        DROP TYPE document_category;
    """)

    op.execute("""
        ALTER TYPE document_category_old RENAME TO document_category;
    """)

    # Restore file_url NOT NULL
    op.alter_column(
        'documents',
        'file_url',
        existing_type=sa.VARCHAR(),
        nullable=False
    )