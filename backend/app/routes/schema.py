from fastapi import APIRouter, Depends
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Session
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.database import Base, get_db
import app.models  # noqa: F401 — registers all models on Base.metadata
from app.schemas import (
    ColumnSchema,
    ForeignKeySchema,
    UniqueConstraintSchema,
    TableSchema,
    SchemaResponse,
    SyncResponse,
)

router = APIRouter(prefix="/api")


@router.get("/schema", response_model=SchemaResponse)
def get_schema():
    tables = []
    for table in Base.metadata.sorted_tables:
        columns = []
        for col in table.columns:
            columns.append(ColumnSchema(
                name=col.name,
                type=str(col.type),
                primary_key=col.primary_key,
                nullable=col.nullable,
                unique=bool(col.unique),
            ))

        foreign_keys = []
        for fk in table.foreign_keys:
            foreign_keys.append(ForeignKeySchema(
                column=fk.parent.name,
                references_table=fk.column.table.name,
                references_column=fk.column.name,
            ))

        unique_constraints = []
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint) and len(constraint.columns) > 1:
                unique_constraints.append(UniqueConstraintSchema(
                    name=constraint.name,
                    columns=[c.name for c in constraint.columns],
                ))

        tables.append(TableSchema(
            name=table.name,
            columns=columns,
            foreign_keys=foreign_keys,
            unique_constraints=unique_constraints,
        ))

    return SchemaResponse(tables=tables)


@router.get("/schema/sync", response_model=SyncResponse)
def get_schema_sync(db: Session = Depends(get_db)):
    connection = db.connection()
    migration_context = MigrationContext.configure(connection)
    diffs = compare_metadata(migration_context, Base.metadata)

    differences = []
    for diff in diffs:
        if isinstance(diff, tuple):
            op = diff[0]
            if op == "add_table":
                differences.append(f"add_table: {diff[1].name}")
            elif op == "remove_table":
                differences.append(f"remove_table: {diff[1].name}")
            elif op == "add_column":
                _, table_name, col = diff[1], diff[2], diff[3]
                differences.append(f"add_column: {table_name}.{col.name} ({col.type})")
            elif op == "remove_column":
                _, table_name, col = diff[1], diff[2], diff[3]
                differences.append(f"remove_column: {table_name}.{col.name} ({col.type})")
            else:
                differences.append(str(diff))
        else:
            differences.append(str(diff))

    return SyncResponse(in_sync=len(differences) == 0, differences=differences)
