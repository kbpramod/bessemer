import "./TestCard.css";

export type TestCase = {
  id: number;
  title: string;
  status: "PASS" | "FAIL";
  runCount: number;
  passCount: number;
  failCount: number;
  details: string;
};

type TestCardProps = {
  testCase: TestCase;
  isOpen: boolean;
  onToggle: () => void;
};

function TestCard({ testCase, isOpen, onToggle }: TestCardProps) {
  const isPassed = testCase.status === "PASS";

  return (
    <div className={`test-card ${isOpen ? "open" : ""}`}>
      {/* Card Header */}
      <div className="test-card-header">
        <div className="test-info">
          <h3>{testCase.title}</h3>

          <span className="run-count">{testCase.runCount} times ran</span>
        </div>

        <div className="test-actions">
          {/* PASS COUNT */}
          <span className="pass-count">✓ {testCase.passCount}</span>

          {/* FAIL COUNT */}
          <span className="fail-count">✕ {testCase.failCount}</span>

          {/* Overall PASS / FAIL */}
          <span className={`status ${isPassed ? "pass" : "fail"}`}>
            {testCase.status}
          </span>

          {/* Open / Close */}
          <button
            className="toggle-button"
            onClick={onToggle}
            aria-label={isOpen ? "Close details" : "Open details"}
          >
            {isOpen ? "⌃" : "⌄"}
          </button>
        </div>
      </div>

      {/* Details */}
      {isOpen && (
        <div className="test-card-details">
          <h4>Test Details</h4>

          <p>{testCase.details}</p>
        </div>
      )}
    </div>
  );
}

export default TestCard;
