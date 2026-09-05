import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { onboardWebsite } from "../../api/client";

function Home() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(""), 3000);
  };

  const handleStartTesting = async () => {
    if (!username || !url || !password) {
      showToast("Please add username, URL and password.");
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await onboardWebsite({
        url,
        accounts: [{ username, password, role: "user" }],
      });

      navigate(`/websites/${result.website.id}`);
    } catch (error) {
      console.error(error);
      showToast(error instanceof Error ? error.message : "Unable to start testing. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {toast && <div className="toast">⚠️ {toast}</div>}

      <main className="main">
        <section className="hero">
          <h1>AI Testing Agent</h1>

          <p>
            Find bugs in your application automatically.
          </p>

          <div className="input-section">
            <label>Application URL
              <input
                type="url"
                placeholder="https://your-app.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </label>

            <label>Username
              <input
                type="text"
                placeholder="username..."
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <label>Password
              <input
                type="password"
                placeholder="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <button
              className="start-button"
              onClick={handleStartTesting}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Starting..." : "Start Testing"}
            </button>

            <button
              className="link-button"
              onClick={() => navigate("/dashboard")}
            >
              View testing dashboard
            </button>
          </div>
        </section>
      </main>
    </>
  );
}

export default Home;
