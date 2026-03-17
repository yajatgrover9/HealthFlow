from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _quote_pg_literal(value: str) -> str:
    """Safely quote a Postgres string literal."""

    return "'" + value.replace("'", "''") + "'"


def ensure_taskstatus_enum(engine: Engine, schema: str = "public") -> None:
    """Best-effort bootstrap for Postgres enum used by VisitTask.status.

    Why it's happening in your environment
    -------------------------------
    Postgres ENUMs are *schema objects* with a fixed list of allowed literals.
    If an enum type `taskstatus` was created earlier with values like:
      ('pending', 'assigned', 'done')
    then any SQL that references the missing literal 'in_progress' will fail *even in SELECTs*.

    This function keeps dev/MVP environments unblocked by:
    - Creating the enum if missing
    - Adding any missing values (including 'in_progress')

    Production note:
    - Replace with Alembic migrations.
    """

    if engine.dialect.name != "postgresql":
        return

    desired = ["pending", "assigned", "in_progress", "done"]

    with engine.begin() as conn:
        # 1) Find enum type (prefer requested schema; otherwise any schema)
        row = (
            conn.execute(
                text(
                    """
                SELECT n.nspname AS schema, t.typname AS name
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typtype = 'e'
                  AND t.typname = 'taskstatus'
                ORDER BY (n.nspname = :preferred_schema) DESC, n.nspname ASC
                LIMIT 1
                """
                ),
                {"preferred_schema": schema},
            )
            .mappings()
            .first()
        )

        enum_schema = row["schema"] if row else schema

        # 2) If missing, create it (NOTE: enum labels can't be bind params)
        if row is None:
            labels_sql = ", ".join(_quote_pg_literal(v) for v in desired)
            conn.execute(
                text(f"CREATE TYPE {enum_schema}.taskstatus AS ENUM ({labels_sql})")
            )
            logger.info("Created enum %s.taskstatus with %s", enum_schema, desired)
            return

        # 3) Add missing values (labels can't be bind params)
        existing_vals = (
            conn.execute(
                text(
                    """
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typtype = 'e'
                  AND t.typname = 'taskstatus'
                  AND n.nspname = :enum_schema
                ORDER BY e.enumsortorder
                """
                ),
                {"enum_schema": enum_schema},
            )
            .scalars()
            .all()
        )

        missing = [v for v in desired if v not in set(existing_vals)]
        for v in missing:
            conn.execute(
                text(
                    f"ALTER TYPE {enum_schema}.taskstatus ADD VALUE IF NOT EXISTS {_quote_pg_literal(v)}"
                )
            )

        if missing:
            logger.info("Updated enum %s.taskstatus; added %s", enum_schema, missing)
        else:
            logger.info("Enum %s.taskstatus already contains %s", enum_schema, desired)
