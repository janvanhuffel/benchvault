from fastapi import APIRouter
from sqlalchemy import UniqueConstraint

from app.database import Base
from app.models import *  # noqa: F401 — ensure all models are registered on Base.metadata
from app.schemas import (
    ColumnSchema,
    ForeignKeySchema,
    UniqueConstraintSchema,
    TableSchema,
    SchemaResponse,
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
