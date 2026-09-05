import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getDaemonStatus,
  listWebsites,
  startDaemon,
  stopDaemon,
  type Website,
} from "../../api/client";
import './Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [daemonRunning, setDaemonRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadWebsites = useCallback(async () => {
    try {
      setWebsites(await listWebsites());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load registered websites.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWebsites();
    getDaemonStatus()
      .then((status) => setDaemonRunning(status.daemon_running))
      .catch(() => setDaemonRunning(false));
  }, [loadWebsites]);

  const handleToggleDaemon = async () => {
    try {
      if (daemonRunning) {
        await stopDaemon();
        setDaemonRunning(false);
      } else {
        await startDaemon({ interval_seconds: 60 });
        setDaemonRunning(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to change the scheduler state.");
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Testing Dashboard</h1>
          <p className="dashboard-subtitle">
            {websites.length} registered website{websites.length === 1 ? "" : "s"}
            {daemonRunning ? " · scheduler running" : ""}
          </p>
        </div>

        <div className="dashboard-actions">
          <button className="prompt-button" onClick={handleToggleDaemon}>
            {daemonRunning ? "Stop Scheduler" : "Start Scheduler"}
          </button>

          <button className="save-prompt-button" onClick={() => navigate("/")}>
            Register Website
          </button>
        </div>
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      {isLoading && <p className="dashboard-empty">Loading websites...</p>}

      {!isLoading && websites.length === 0 && (
        <p className="dashboard-empty">
          No websites registered yet. Register one to start testing.
        </p>
      )}

      <div className="website-list">
        {websites.map((website) => (
          <button
            key={website.id}
            className="website-row"
            onClick={() => navigate(`/websites/${website.id}`)}
          >
            <div className="website-row-main">
              <h3>{website.domain}</h3>
              <span className="website-row-url">{website.url}</span>
            </div>

            <div className="website-row-meta">
              <span className={`status ${website.is_active ? "pass" : "pending"}`}>
                {website.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
              <span className="website-row-id">ID {website.id}</span>
              <span className="website-row-chevron">›</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
