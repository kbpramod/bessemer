import type { SuiteResult, TestSchedule } from "../../api/client";
import "./TestCard.css";

type TestCardProps = {
  schedule: TestSchedule;
  result?: SuiteResult;
  isOpen: boolean;
  isRunning: boolean;
  onToggle: () => void;
  onRunNow: () => void;
};

const RESULT_LABELS: Record<SuiteResult["status"], string> = {
  PASSED: "PASS",
  CONFIRMED_BUG: "BUG",
  FAILED_AUTOMATION: "FAIL",
  SUSPECTED_APP_FAILURE: "SUSPECT",
};

function formatTimestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "never";
}

function TestCard({ schedule, result, isOpen, isRunning, onToggle, onRunNow }: TestCardProps) {
  const isPassed = result?.status === "PASSED";
  const statusLabel = result ? RESULT_LABELS[result.status] : "PENDING";

  return (
    <div className={`test-card ${isOpen ? "open" : ""}`}>
      <div className="test-card-header">
        <div className="test-info">
          <h3>{schedule.title}</h3>

          <span className="run-count">
            every {schedule.cron_interval_hours}h · last run {formatTimestamp(schedule.last_run_at)}
          </span>
        </div>

        <div className="test-actions">
          {schedule.is_due && <span className="due-badge">DUE</span>}

          <span className={`status ${result ? (isPassed ? "pass" : "fail") : "pending"}`}>
            {statusLabel}
          </span>

          <button
            className="run-now-button"
            onClick={(e) => {
              e.stopPropagation();
              onRunNow();
            }}
            disabled={isRunning}
          >
            {isRunning ? "Running..." : "Run Now"}
          </button>

          <button
            className="toggle-button"
            onClick={onToggle}
            aria-label={isOpen ? "Close details" : "Open details"}
          >
            {isOpen ? "⌃" : "⌄"}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="test-card-details">
          <h4>Test Details</h4>

          <p>ID: {schedule.test_id}</p>
          <p>Domain: {schedule.domain}</p>
          <p>Next run: {formatTimestamp(schedule.next_run_at)}</p>

          {result ? (
            <>
              <p>Latest outcome: {result.status}</p>
              {result.duration_s !== undefined && <p>Duration: {result.duration_s}s</p>}
              {result.heals_needed !== undefined && <p>Self-heal attempts: {result.heals_needed}</p>}
              {result.incident_id && <p>Incident: {result.incident_id}</p>}
              {result.error && <p>{result.error}</p>}
            </>
          ) : (
            <p>This test has not run in the current session yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default TestCard;
