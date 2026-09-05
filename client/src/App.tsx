import { useState } from 'react'
import './App.css'
import Header from './components/Header/Header';
import Dashboard from './components/Dashboard/Dashboard';


function App() {
  const [url, setUrl] = useState('');
  const [username,setUsername]=useState('');
  const [password,setPassword] =useState('');
  const [showDashboard,setShowDashboard]=useState(false);
  const [toast, setToast] = useState("");

  const handleStartTesting = async() => {
    if (!username || !url || !password) {
    setToast("Please add username, URL and password.");

    setTimeout(() => {
      setToast("");
    }, 3000);

    return;
  }

    const data = {
    url,
    username,
    password,
  };

  try {
    const response = await fetch("http://localhost:8000/start-testing", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error("Failed to start testing");
    }

    const result = await response.json();

    console.log("Backend response:", result);

    setShowDashboard(true);
  } catch (error) {
    console.error(error);

    setToast("Unable to start testing. Please try again.");

    setTimeout(() => {
      setToast("");
    }, 3000);
  }
  }

  return (
    <div className="app">
      {toast && (
  <div className="toast">
    ⚠️ {toast}
  </div>
)}
      <Header/>
      {!showDashboard?
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
            >
              Start Testing
            </button>
          </div>
        </section>
      </main>
      :
      <Dashboard setShowDashboard={setShowDashboard}/>
}
    </div>
  )
}

export default App