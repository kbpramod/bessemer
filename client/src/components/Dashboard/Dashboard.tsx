import { useState } from "react";
import type { TestCase } from "../TestCard/TestCard";
import TestCard from "../TestCard/TestCard";
import './Dashboard.css';
// import TestCard, { TestCase } from "./TestCard";

const testCases: TestCase[] = [
  {
    id: 1,
    title: "Login with valid credentials",
    status: "PASS",
    runCount: 5,
    passCount: 5,
    failCount: 0,
    details: "Login worked successfully on all runs.",
  },
  {
    id: 2,
    title: "Checkout with valid card",
    status: "FAIL",
    runCount: 5,
    passCount: 3,
    failCount: 2,
    details: "Checkout failed on two runs because of a payment error.",
  },
];

function Dashboard({setShowDashboard}) {
  const [openId, setOpenId] = useState<number | null>(null);
   const [showPrompt, setShowPrompt] = useState(false);
const [prompt, setPrompt] = useState("");

  const handleDifferentCredentials=()=>{
    setShowDashboard(false);
  }

  return (
    <div className="dashboard">
{(
  <div className="dashboard">
    <div className="dashboard-header">
      <h1>Testing Dashboard</h1>

      <button
        className="prompt-button"
        onClick={() => setShowPrompt((prev) => !prev)}
      >
        {showPrompt ? "Close Prompt" : "Add Prompt"}
      </button>
    </div>

    {showPrompt && (
      <div className="prompt-section">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your testing prompt..."
          rows={5}
        />

        <button
          className="save-prompt-button"
          onClick={() => {
            console.log("Prompt:", prompt);
            setShowPrompt(false);
          }}
        >
          Save Prompt
        </button>
      </div>
    )}

    <div className="test-cards">
      {testCases.map((testCase) => (
        <TestCard
          key={testCase.id}
          testCase={testCase}
          isOpen={openId === testCase.id}
          onToggle={() =>
            setOpenId(
              openId === testCase.id
                ? null
                : testCase.id
            )
          }
        />
      ))}
    </div>
  </div>
)}
<div className="button-container">
<button className="credentials-button" onClick={handleDifferentCredentials} > Add Different Credentials </button>
</div>
    </div>
  );
}

export default Dashboard;
