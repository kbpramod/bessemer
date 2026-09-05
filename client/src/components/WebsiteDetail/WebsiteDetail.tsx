import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import TestCard from "../TestCard/TestCard";
import {
  addAccount,
  deleteWebsite,
  getOnboardingDetails,
  getTestSchedules,
  getWebsiteRuns,
  onboardingEventsUrl,
  runCronCycle,
  runDiscovery,
  runTestNow,
  type Account,
  type CronRunResult,
  type SuiteResult,
  type TestRun,
  type TestSchedule,
  type Website,
} from "../../api/client";
import "./WebsiteDetail.css";

type Tab = "tests" | "runs" | "settings";

const TABS: { key: Tab; label: string }[] = [
  { key: "tests", label: "Test Cases" },
  { key: "runs", label: "Tests Ran" },
  { key: "settings", label: "Settings" },
];

function formatTimestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "never";
}

function WebsiteDetail() {
  const { websiteId } = useParams();
  const navigate = useNavigate();
  const id = Number(websiteId);

  const [website, setWebsite] = useState<Website | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [schedules, setSchedules] = useState<TestSchedule[]>([]);
  const [dueCount, setDueCount] = useState(0);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [results, setResults] = useState<Record<string, SuiteResult>>({});
  const [lastRun, setLastRun] = useState<CronRunResult | null>(null);

  const [tab, setTab] = useState<Tab>("tests");
  const [openId, setOpenId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  const [newAccount, setNewAccount] = useState({ username: "", password: "", role: "user" });
  const [isAddingAccount, setIsAddingAccount] = useState(false);

  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryEvents, setDiscoveryEvents] = useState<string[]>([]);
  const streamRef = useRef<EventSource | null>(null);

  const [runningTestId, setRunningTestId] = useState<string | null>(null);

  const loadTestData = useCallback(async (domain: string) => {
    const [schedule, runHistory] = await Promise.all([
      getTestSchedules(domain),
      getWebsiteRuns(id),
    ]);

    setSchedules(schedule.schedules);
    setDueCount(schedule.due_count);
    setRuns(runHistory.runs);
  }, [id]);

  const loadAll = useCallback(async () => {
    if (!Number.isInteger(id)) {
      setError("Invalid website id.");
      setIsLoading(false);
      return;
    }

    try {
      const details = await getOnboardingDetails(id);
      setWebsite(details.website);
      setAccounts(details.accounts);
      await loadTestData(details.website.domain);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load website details.");
    } finally {
      setIsLoading(false);
    }
  }, [id, loadTestData]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // Close any open progress stream when leaving the page.
  useEffect(() => () => streamRef.current?.close(), []);

  const handleRunDiscovery = async () => {
    setIsDiscovering(true);
    setDiscoveryEvents([]);
    setError("");

    try {
      const started = await runDiscovery(id);
      setDiscoveryEvents([started.message]);

      streamRef.current?.close();
      const stream = new EventSource(onboardingEventsUrl(id));
      streamRef.current = stream;

      stream.onmessage = (event) => {
        setDiscoveryEvents((prev) => [...prev, event.data]);

        // The graph publishes a terminal message when it finishes either way.
        if (event.data.includes("completed") || event.data.includes("failed")) {
          stream.close();
          streamRef.current = null;
          setIsDiscovering(false);
          loadAll();
        }
      };

      stream.onerror = () => {
        stream.close();
        streamRef.current = null;
        setIsDiscovering(false);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start discovery.");
      setIsDiscovering(false);
    }
  };

  const handleRunNow = async () => {
    if (!website) return;

    setIsRunning(true);
    setError("");

    try {
      const result = await runCronCycle({ domain: website.domain });
      setLastRun(result);
      setResults(Object.fromEntries(result.suite_summary.map((entry) => [entry.id, entry])));
      await loadTestData(website.domain);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run the test cycle.");
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunTestNow = async (testId: string) => {
    if (!website) return;

    setRunningTestId(testId);
    setError("");

    try {
      const { result } = await runTestNow(testId);
      setResults((prev) => ({ ...prev, [testId]: result }));
      await loadTestData(website.domain);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to run test '${testId}'.`);
    } finally {
      setRunningTestId(null);
    }
  };

  const handleAddAccount = async () => {
    if (!newAccount.username || !newAccount.password) {
      setError("Username and password are required to add an account.");
      return;
    }

    setIsAddingAccount(true);

    try {
      const created = await addAccount(id, newAccount);
      setAccounts((prev) => [...prev, created]);
      setNewAccount({ username: "", password: "", role: "user" });
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add the account.");
    } finally {
      setIsAddingAccount(false);
    }
  };

  const handleDelete = async () => {
    if (!website) return;

    const confirmed = window.confirm(
      `Delete ${website.domain}? This also removes its accounts and tests.`
    );
    if (!confirmed) return;

    try {
      await deleteWebsite(id);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete the website.");
    }
  };

  if (isLoading) {
    return <div className="detail"><p className="dashboard-empty">Loading website...</p></div>;
  }

  if (!website) {
    return (
      <div className="detail">
        <button className="link-button" onClick={() => navigate("/dashboard")}>← Back to dashboard</button>
        <div className="dashboard-error">{error || "Website not found."}</div>
      </div>
    );
  }

  return (
    <div className="detail">
      <button className="link-button" onClick={() => navigate("/dashboard")}>← Back to dashboard</button>

      <div className="detail-header">
        <div>
          <h1>{website.domain}</h1>
          <p className="dashboard-subtitle">
            ID {website.id} · {website.url} · {schedules.length} test{schedules.length === 1 ? "" : "s"} · {dueCount} due
          </p>
        </div>

        <div className="detail-actions">
          <button className="prompt-button" onClick={() => loadAll()}>
            Refresh
          </button>

          <button className="prompt-button" onClick={handleRunDiscovery} disabled={isDiscovering}>
            {isDiscovering ? "Discovering..." : "Run Discovery"}
          </button>

          <button className="save-prompt-button" onClick={handleRunNow} disabled={isRunning}>
            {isRunning ? "Running..." : "Run Due Tests"}
          </button>
        </div>
      </div>

      {discoveryEvents.length > 0 && (
        <div className="discovery-log">
          <div className="discovery-log-header">
            <strong>Discovery progress</strong>
            <button className="link-button" onClick={() => setDiscoveryEvents([])}>clear</button>
          </div>

          <ul>
            {discoveryEvents.map((event, index) => (
              <li key={`${index}-${event}`}>{event}</li>
            ))}
          </ul>

          {isDiscovering && <p className="discovery-hint">Discovery runs in the background; this can take a few minutes.</p>}
        </div>
      )}

      <div className="tab-bar">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            className={`tab ${tab === key ? "active" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      {lastRun && tab === "tests" && (
        <div className="run-summary">
          {lastRun.status === "idle"
            ? "No tests were due in the last cycle."
            : `Last cycle: ${lastRun.executed_count} executed · ${lastRun.passed_count ?? 0} passed · ${lastRun.bug_count ?? 0} bugs confirmed · ${lastRun.failed_count ?? 0} automation failures`}
        </div>
      )}

      {tab === "tests" && (
        <div className="test-cards">
          {schedules.length === 0 ? (
            <p className="dashboard-empty">
              No active tests for {website.domain} yet. Tests appear here once the agent has discovered and built them.
            </p>
          ) : (
            schedules.map((schedule) => (
              <TestCard
                key={schedule.test_id}
                schedule={schedule}
                result={results[schedule.test_id]}
                isOpen={openId === schedule.test_id}
                isRunning={runningTestId === schedule.test_id}
                onToggle={() => setOpenId(openId === schedule.test_id ? null : schedule.test_id)}
                onRunNow={() => handleRunTestNow(schedule.test_id)}
              />
            ))
          )}
        </div>
      )}

      {tab === "runs" && (
        <div className="runs-table">
          {runs.length === 0 ? (
            <p className="dashboard-empty">No test executions recorded for this website yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Executed</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.run_id}>
                    <td>{run.title}</td>
                    <td>
                      <span className={`status ${run.status === "PASSED" ? "pass" : "fail"}`}>
                        {run.status}
                      </span>
                    </td>
                    <td>{run.duration_s}s</td>
                    <td>{formatTimestamp(run.executed_at)}</td>
                    <td className="run-error">{run.error_summary ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "settings" && (
        <div className="settings">
          <section className="settings-block">
            <h3>Website</h3>
            <dl>
              <div><dt>URL</dt><dd>{website.url}</dd></div>
              <div><dt>Domain</dt><dd>{website.domain}</dd></div>
              <div><dt>Status</dt><dd>{website.is_active ? "Active" : "Inactive"}</dd></div>
              <div><dt>Registered</dt><dd>{formatTimestamp(website.created_at)}</dd></div>
              <div><dt>Last discovered</dt><dd>{formatTimestamp(website.last_discovered_at)}</dd></div>
            </dl>
          </section>

          <section className="settings-block">
            <h3>Accounts ({accounts.length})</h3>

            {accounts.length === 0 ? (
              <p className="dashboard-empty">No accounts registered for this website.</p>
            ) : (
              <ul className="account-list">
                {accounts.map((account) => (
                  <li key={account.id}>
                    <span>{account.username}</span>
                    <span className="account-role">{account.role}</span>
                    <span className={`status ${account.is_active ? "pass" : "pending"}`}>
                      {account.is_active ? "ACTIVE" : "INACTIVE"}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <div className="account-form">
              <input
                type="text"
                placeholder="username"
                value={newAccount.username}
                onChange={(e) => setNewAccount({ ...newAccount, username: e.target.value })}
              />
              <input
                type="password"
                placeholder="password"
                value={newAccount.password}
                onChange={(e) => setNewAccount({ ...newAccount, password: e.target.value })}
              />
              <input
                type="text"
                placeholder="role"
                value={newAccount.role}
                onChange={(e) => setNewAccount({ ...newAccount, role: e.target.value })}
              />
              <button
                className="save-prompt-button"
                onClick={handleAddAccount}
                disabled={isAddingAccount}
              >
                {isAddingAccount ? "Adding..." : "Add Account"}
              </button>
            </div>
          </section>

          <section className="settings-block danger">
            <h3>Danger Zone</h3>
            <p>Deleting this website also removes its accounts and tests.</p>
            <button className="delete-button" onClick={handleDelete}>Delete Website</button>
          </section>
        </div>
      )}
    </div>
  );
}

export default WebsiteDetail;
