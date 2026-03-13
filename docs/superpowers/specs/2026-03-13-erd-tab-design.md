# ERD Tab Design

## Goal

Add a "Schema" tab to the frontend that renders an interactive Entity Relationship Diagram, auto-generated from the SQLAlchemy model definitions. The ERD stays in sync with schema changes — no manual updates needed.

## Decisions

- **Data source**: SQLAlchemy `Base.metadata.tables` (option B). No DB introspection. Reads Python model definitions at runtime.
- **Detail level**: Full — columns, types, PK, FK, nullable, unique constraints.
- **Rendering**: React Flow with dagre auto-layout. Interactive (zoom, pan, drag).
- **No new backend dependencies**. Frontend adds `reactflow` and `dagre`.

## Backend

### New endpoint: `GET /api/schema`

File: `backend/app/routes/schema.py`

Iterates `Base.metadata.sorted_tables` and returns:

```json
{
  "tables": [
    {
      "name": "benchmark_runs",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "primary_key": true,
          "nullable": false,
          "unique": false
        },
        {
          "name": "project_id",
          "type": "INTEGER",
          "primary_key": false,
          "nullable": false,
          "unique": false
        }
      ],
      "foreign_keys": [
        {
          "column": "project_id",
          "references_table": "projects",
          "references_column": "id"
        }
      ],
      "unique_constraints": [
        {
          "name": "uq_run_metric",
          "columns": ["run_id", "metric_id"]
        }
      ]
    }
  ]
}
```

Implementation: loop over `Base.metadata.sorted_tables`, for each table:
- `table.columns` for column info (name, type string, primary_key, nullable)
- `table.foreign_keys` for FK relationships
- `table.constraints` filtered to `UniqueConstraint` for multi-column uniques
- Column-level unique derived from `column.unique`

Register router in `main.py`.

### Pydantic response schemas

Add to `schemas.py` (or a new `schemas/schema.py` if preferred — but existing convention is single file):

- `ColumnSchema(name, type, primary_key, nullable, unique)`
- `ForeignKeySchema(column, references_table, references_column)`
- `UniqueConstraintSchema(name, columns)`
- `TableSchema(name, columns, foreign_keys, unique_constraints)`
- `SchemaResponse(tables)`

## Frontend

### New page: `SchemaERD.jsx`

Route: `/schema`

1. Fetch `GET /api/schema` on mount via `api.js` (`getSchema()`)
2. Convert each table to a React Flow node:
   - Custom node component `TableNode` renders a card with:
     - Table name as header
     - Column rows: `name : TYPE` with badges for PK, FK, UQ, NULL
   - Position calculated by dagre layout
3. Convert foreign keys to React Flow edges:
   - Source: FK column's table node
   - Target: referenced table node
   - Label: `column -> table.column`
4. Render with `<ReactFlow>` including `<Controls>` and `<Background>`

### Navigation

Add "Schema" link in `App.jsx` nav, route `/schema`.

### API function

Add `getSchema()` to `api.js`.

### Styling

Add to `App.css`:
- `.table-node` — card style matching existing project cards
- `.table-node-header` — table name
- `.table-node-column` — column row
- `.column-badge` variants — PK (accent), FK (secondary), UQ, NULL

### Dependencies

```bash
cd frontend && npm install reactflow dagre
```

## What changes when you modify models.py

1. Edit `models.py` (add/remove table, column, FK, constraint)
2. Container restarts (uvicorn `--reload` in dev)
3. `GET /api/schema` returns updated structure
4. ERD re-renders on next page visit

No migration, no build step, no manual update.
