import { useState } from "react";

import { runBenchmark } from "../api";
import type { BenchmarkComparison } from "../types";

export function BenchmarkPanel({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const [result, setResult] = useState<BenchmarkComparison | null>(null);
  const [pending, setPending] = useState(false);

  async function run() {
    setPending(true);
    try {
      setResult(await runBenchmark());
    } catch (error) {
      onError(error instanceof Error ? error.message : "Benchmark failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="data-panel benchmark-panel">
      <div className="section-heading">
        <div>
          <span className="section-kicker">REPRODUCIBLE TEST</span>
          <h2>Scheduler benchmark</h2>
        </div>
        <button disabled={pending} onClick={run}>
          {pending ? "Running…" : "Compare strategies"}
        </button>
      </div>
      {!result ? (
        <p className="benchmark-intro">
          Run the same six jobs with identical robots and batteries. Only the
          assignment algorithm changes.
        </p>
      ) : (
        <>
          <p className="benchmark-scenario">{result.scenario}</p>
          <div className="benchmark-table">
            <span>Strategy</span><span>Efficiency</span><span>Throughput</span><span>Avg delivery</span>
            <strong>Nearest robot</strong>
            <strong>{result.baseline.efficiency_score}</strong>
            <strong>{result.baseline.throughput}</strong>
            <strong>{result.baseline.average_delivery_ticks} ticks</strong>
            <strong>Traffic + energy</strong>
            <strong>{result.optimized.efficiency_score}</strong>
            <strong>{result.optimized.throughput}</strong>
            <strong>{result.optimized.average_delivery_ticks} ticks</strong>
          </div>
          <p className="benchmark-win">
            {result.improvement.overall_efficiency_percent}% higher overall efficiency ·{" "}
            {result.improvement.throughput_percent}% higher throughput ·{" "}
            {result.improvement.delivery_time_percent}% faster delivery
          </p>
          <p className="benchmark-formula">
            Score: {result.efficiency_formula.throughput}% throughput ·{" "}
            {result.efficiency_formula.delivery_speed}% delivery speed ·{" "}
            {result.efficiency_formula.reduced_waiting}% waiting ·{" "}
            {result.efficiency_formula.reduced_charging}% charging
          </p>
        </>
      )}
    </section>
  );
}
