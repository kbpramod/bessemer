import { useState } from 'react'
import './App.css'
import Header from './components/Header/Header'

function App() {
  const [url, setUrl] = useState('');
  const [username,setUsername]=useState('');
  const [password,setPassword] =useState('');

  const handleStartTesting = () => {
    
  }

  return (
    <div className="app">
      <Header/>

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
    </div>
  )
}

export default App