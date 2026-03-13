import { useEffect, useState, useCallback } from "react";
import ReactFlow, { Controls, Background, useNodesState, useEdgesState } from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";
import { getSchema, getSchemaSync } from "../api";
import TableNode from "../components/TableNode";

const nodeTypes = { table: TableNode };

const NODE_WIDTH = 320;
const NODE_ROW_HEIGHT = 24;
const NODE_HEADER_HEIGHT = 40;
const NODE_CONSTRAINT_HEIGHT = 22;
const NODE_PADDING = 16;

function estimateNodeHeight(table) {
  const columnsHeight = table.columns.length * NODE_ROW_HEIGHT;
  const constraintsHeight = table.unique_constraints.length > 0
    ? NODE_CONSTRAINT_HEIGHT * table.unique_constraints.length + 8
    : 0;
  return NODE_HEADER_HEIGHT + columnsHeight + constraintsHeight + NODE_PADDING;
}

function buildLayout(tables) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 120 });

  tables.forEach((table) => {
    const height = estimateNodeHeight(table);
    g.setNode(table.name, { width: NODE_WIDTH, height });
  });

  tables.forEach((table) => {
    table.foreign_keys.forEach((fk) => {
      g.setEdge(table.name, fk.references_table);
    });
  });

  dagre.layout(g);

  const nodes = tables.map((table) => {
    const pos = g.node(table.name);
    return {
      id: table.name,
      type: "table",
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - pos.height / 2 },
      data: { table },
    };
  });

  const edges = [];
  tables.forEach((table) => {
    table.foreign_keys.forEach((fk) => {
      edges.push({
        id: `${table.name}.${fk.column}->${fk.references_table}.${fk.references_column}`,
        source: table.name,
        target: fk.references_table,
        label: `${fk.column} → ${fk.references_table}.${fk.references_column}`,
        type: "smoothstep",
        animated: true,
      });
    });
  });

  return { nodes, edges };
}

export default function SchemaERD() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [syncExpanded, setSyncExpanded] = useState(false);

  useEffect(() => {
    getSchema()
      .then((data) => {
        const { nodes: n, edges: e } = buildLayout(data.tables);
        setNodes(n);
        setEdges(e);
      })
      .catch(() => setError("Failed to load schema"))
      .finally(() => setLoading(false));

    getSchemaSync()
      .then(setSyncStatus)
      .catch(() => setSyncStatus({ in_sync: false, differences: ["Failed to reach database"] }));
  }, [setNodes, setEdges]);

  const toggleSync = useCallback(() => setSyncExpanded((v) => !v), []);

  if (loading) return <p className="empty-state">Loading schema...</p>;
  if (error) return <p className="empty-state">{error}</p>;

  return (
    <div className="erd-container">
      <div className="erd-header">
        <h1>Schema</h1>
        {syncStatus === null ? (
          <span className="sync-badge sync-loading">Checking sync...</span>
        ) : syncStatus.in_sync ? (
          <span className="sync-badge sync-ok">In Sync</span>
        ) : (
          <button className="sync-badge sync-error" onClick={toggleSync}>
            Out of Sync ({syncStatus.differences.length})
          </button>
        )}
      </div>
      {syncStatus && !syncStatus.in_sync && syncExpanded && (
        <div className="sync-details">
          <ul>
            {syncStatus.differences.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="erd-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}
