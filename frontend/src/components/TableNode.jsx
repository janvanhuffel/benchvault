import { Handle, Position } from "reactflow";

function getBadges(col, fkColumns) {
  const badges = [];
  if (col.primary_key) badges.push({ label: "PK", cls: "badge-pk" });
  if (fkColumns.has(col.name)) badges.push({ label: "FK", cls: "badge-fk" });
  if (col.unique) badges.push({ label: "UQ", cls: "badge-uq" });
  if (col.nullable) badges.push({ label: "NULL", cls: "badge-null" });
  return badges;
}

export default function TableNode({ data }) {
  const { table } = data;
  const fkColumns = new Set(table.foreign_keys.map((fk) => fk.column));

  return (
    <div className="table-node">
      <Handle type="target" position={Position.Left} />
      <div className="table-node-header">{table.name}</div>
      <div className="table-node-columns">
        {table.columns.map((col) => (
          <div key={col.name} className="table-node-column">
            <span className="column-name">{col.name}</span>
            <span className="column-type">{col.type}</span>
            <span className="column-badges">
              {getBadges(col, fkColumns).map((b) => (
                <span key={b.label} className={`column-badge ${b.cls}`}>
                  {b.label}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
      {table.unique_constraints.length > 0 && (
        <div className="table-node-constraints">
          {table.unique_constraints.map((uq) => (
            <div key={uq.name || uq.columns.join(",")} className="table-node-constraint">
              UQ: {uq.columns.join(", ")}
            </div>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
