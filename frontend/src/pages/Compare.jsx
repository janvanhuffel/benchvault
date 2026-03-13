import { useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { compareRuns } from "../api";

function getHslColor(value) {
  // Clamp to [0, 1]
  const v = Math.max(0, Math.min(1, value));
  // red(0) → yellow(60) → green(120)
  const hue = v * 120;
  return `hsla(${hue}, 70%, 45%, 0.45)`;
}

export default function Compare() {
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get("run_ids");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [fetchDone, setFetchDone] = useState(false);
  const [metricOrder, setMetricOrder] = useState(null);

  const fetchComparison = useCallback((ids) => {
    compareRuns(ids)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setFetchDone(true));
  }, []);

  useEffect(() => {
    if (!idsParam) return;
    const ids = idsParam.split(",").map(Number);
    fetchComparison(ids);
  }, [idsParam, fetchComparison]);

  const perClass = useMemo(() => data?.per_class_metrics || [], [data]);

  const initialOrder = useMemo(
    () => perClass.map((g) => g.metric_name),
    [perClass]
  );

  const order = metricOrder ?? initialOrder;

  const orderedPerClass = useMemo(
    () => order.map((name) => perClass.find((g) => g.metric_name === name)).filter(Boolean),
    [order, perClass]
  );

  const moveGroup = useCallback(
    (index, direction) => {
      const newOrder = [...order];
      const swapIndex = index + direction;
      if (swapIndex < 0 || swapIndex >= newOrder.length) return;
      [newOrder[index], newOrder[swapIndex]] = [newOrder[swapIndex], newOrder[index]];
      setMetricOrder(newOrder);
    },
    [order]
  );

  if (!idsParam)
    return <p className="empty-state">No runs selected for comparison. Go back and select runs.</p>;
  if (!fetchDone) return <p className="empty-state">Loading comparison...</p>;
  if (error) return <p className="empty-state">{error}</p>;
  if (!data) return null;

  // For each metric, find the best value across runs
  const getBestValue = (metricName) => {
    const hib = data.higher_is_better[metricName];
    const values = data.runs
      .map((run) => {
        const metric = run.metrics.find((m) => m.metric_name === metricName);
        return metric ? metric.value : null;
      })
      .filter((v) => v !== null);

    if (values.length === 0) return null;
    return hib ? Math.max(...values) : Math.min(...values);
  };

  const getMetricValue = (run, metricName) => {
    const metric = run.metrics.find((m) => m.metric_name === metricName);
    return metric ? metric.value : null;
  };

  // Check if runs have different dataset versions (for info message)
  const datasetVersions = new Set(data.runs.map((r) => `${r.dataset}/${r.dataset_version}`));
  const hasMixedVersions = datasetVersions.size > 1;

  return (
    <div>
      <h1>Run Comparison</h1>

      {/* Scalar metrics table */}
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            {data.runs.map((run) => (
              <th key={run.id} className="metric-value">
                {run.model_name} / {run.model_version} (ep {run.epoch})
                <br />
                <span className="text-secondary" style={{ fontWeight: "normal" }}>
                  {run.dataset} {run.dataset_version}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.metric_names.map((metricName) => {
            const best = getBestValue(metricName);
            return (
              <tr key={metricName}>
                <td style={{ fontWeight: 500 }}>
                  {metricName}
                  <span className="text-muted" style={{ marginLeft: "0.5rem" }}>
                    ({data.higher_is_better[metricName] ? "\u2191" : "\u2193"})
                  </span>
                </td>
                {data.runs.map((run) => {
                  const val = getMetricValue(run, metricName);
                  const isBest = val !== null && val === best;
                  return (
                    <td
                      key={run.id}
                      className={`metric-value${isBest ? " metric-best" : ""}`}
                    >
                      {val !== null ? val.toFixed(4) : "\u2014"}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Per-class metrics section */}
      {hasMixedVersions && perClass.length === 0 && (
        <p className="pcm-info">
          Per-class comparison is only available when all runs use the same dataset version.
        </p>
      )}

      {perClass.length > 0 && (
        <div className="pcm-section">
          <h2>Per-Class Metrics</h2>
          <div style={{ overflowX: "auto" }}>
            <table className="pcm-table">
              <thead>
                <tr>
                  <th rowSpan={2} style={{ textAlign: "left" }}>Class</th>
                  {orderedPerClass.map((group, gi) => (
                    <th
                      key={group.metric_name}
                      colSpan={data.runs.length}
                      className={`pcm-group-header${gi > 0 ? " pcm-group-sep" : ""}`}
                    >
                      {group.metric_name} ({group.higher_is_better ? "\u2191" : "\u2193"})
                      <span className="pcm-reorder-btns">
                        <button
                          className="pcm-reorder-btn"
                          onClick={() => moveGroup(gi, -1)}
                          disabled={gi === 0}
                          aria-label={`Move ${group.metric_name} left`}
                          title="Move left"
                        >
                          &#8592;
                        </button>
                        <button
                          className="pcm-reorder-btn"
                          onClick={() => moveGroup(gi, 1)}
                          disabled={gi === orderedPerClass.length - 1}
                          aria-label={`Move ${group.metric_name} right`}
                          title="Move right"
                        >
                          &#8594;
                        </button>
                      </span>
                    </th>
                  ))}
                </tr>
                <tr>
                  {orderedPerClass.map((group, gi) =>
                    data.runs.map((run, ri) => (
                      <th
                        key={`${group.metric_name}-${run.id}`}
                        className={gi > 0 && ri === 0 ? "pcm-group-sep" : ""}
                      >
                        {run.model_name} / {run.model_version} (ep {run.epoch})
                      </th>
                    ))
                  )}
                </tr>
              </thead>
              <tbody>
                {orderedPerClass[0].classes.map((className) => (
                  <tr key={className}>
                    <td className="pcm-class-name">{className}</td>
                    {orderedPerClass.map((group, gi) => {
                      // Find best value for this class across runs
                      const classValues = group.runs
                        .map((rv) => rv.values[className])
                        .filter((v) => v !== undefined && v !== null);
                      const best = classValues.length > 0
                        ? (group.higher_is_better ? Math.max(...classValues) : Math.min(...classValues))
                        : null;

                      return data.runs.map((run, ri) => {
                        const runData = group.runs.find((rv) => rv.run_id === run.id);
                        const val = runData?.values[className];
                        const isBest = val !== undefined && val !== null && val === best && classValues.length > 1;

                        return (
                          <td
                            key={`${group.metric_name}-${className}-${run.id}`}
                            className={gi > 0 && ri === 0 ? "pcm-group-sep" : ""}
                            style={{
                              backgroundColor: val !== undefined && val !== null ? getHslColor(val) : undefined,
                              fontWeight: isBest ? "bold" : undefined,
                              fontVariantNumeric: "tabular-nums",
                            }}
                          >
                            {val !== undefined && val !== null ? val.toFixed(4) : "\u2014"}
                          </td>
                        );
                      });
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
