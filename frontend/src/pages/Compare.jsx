import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { compareRuns } from "../api";

export default function Compare() {
  const [searchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const idsParam = searchParams.get("run_ids");
    if (!idsParam) {
      setLoading(false);
      setError("No runs selected for comparison. Go back and select runs.");
      return;
    }
    const ids = idsParam.split(",").map(Number);
    compareRuns(ids)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [searchParams]);

  if (loading) return <p>Loading comparison...</p>;
  if (error) return <p>{error}</p>;
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

  return (
    <div>
      <h1>Run Comparison</h1>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            {data.runs.map((run) => (
              <th key={run.id}>
                {run.model_name} / {run.model_version}
                <br />
                <small style={{ fontWeight: "normal", color: "#666" }}>
                  {run.dataset} {run.dataset_version}
                </small>
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
                  <small style={{ color: "#888", marginLeft: "0.5rem" }}>
                    ({data.higher_is_better[metricName] ? "\u2191" : "\u2193"})
                  </small>
                </td>
                {data.runs.map((run) => {
                  const val = getMetricValue(run, metricName);
                  const isBest = val !== null && val === best;
                  return (
                    <td
                      key={run.id}
                      style={{
                        background: isBest ? "#d4edda" : "transparent",
                        fontWeight: isBest ? 600 : 400,
                      }}
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
    </div>
  );
}
