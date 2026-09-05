# AI Testing Agent Self-Healing Web Testing Architecture

AI Testing Agent separates one-time application understanding from continuous test execution. Playwright supplies deterministic browser evidence; LLM-based components reason over that structured evidence for hypothesis generation, diagnosis, healing, and verification.

```mermaid
flowchart TD
    Input([Application entry point]) --> Onboarding

    subgraph AITestingAgent[AI Testing Agent]
        subgraph Onboarding[Onboarding Graph]
            OStart[Start or genuinely new state]
            ODiscover[Discovery\nPlaywright + structured page/state model]
            Hypotheses[Hypothesis Generator\nSmoke and flow hypotheses]
            Builder[Builder\nGenerate Playwright tests]
            OStart --> ODiscover --> Hypotheses --> Builder
        end

        subgraph Continuous[Cron Graph]
            Queue[Get next test]
            Runner[Runner\nExecute Playwright test]
            Observer[Observer\nScreenshots, console, network, runtime evidence]
            Analyzer[Analyzer\nStructured verdict]
            Queue --> Runner --> Observer --> Analyzer

            Analyzer -->|PASS| Next([Continue queue])
            Analyzer -->|NEED_HEAL| Healer[Healer\nRepair plan]
            Healer --> FreshHeal[Fresh Discovery\nCurrent DOM and browser state]
            FreshHeal --> Editor[Editor\nApply repair plan]
            Editor --> Runner

            Analyzer -->|SUSPECTED_APP_FAILURE| Verifier[Verifier\nIndependent validation]
            Verifier --> FreshVerify[Fresh Discovery]
            Verifier --> FocusedSmoke[Focused smoke test]
            FreshVerify --> VerifierLLM[Verifier LLM]
            FocusedSmoke --> VerifierLLM
            VerifierLLM -->|CONFIRMED_APP_BUG| Report[Report defect\nEvidence + execution history]
            VerifierLLM -->|NOT_CONFIRMED| HealOrDiscard[Heal or discard]
            HealOrDiscard --> Healer
        end

        Discovery[Reusable Discovery capability\nPlaywright is browser truth]
        AppModel[(Application Model\nKnown screens, states, structure)]
        TestRepo[(Test Repository\nTests, metadata, status, history, healing)]
    end

    Builder -->|Persist generated tests| TestRepo
    TestRepo -->|Select stored tests| Queue
    ODiscover -->|Update known state| AppModel
    ODiscover --> Discovery
    FreshHeal --> Discovery
    FreshVerify --> Discovery
    Discovery --> AppModel
    Analyzer -->|New screen/state| AppModel
    AppModel -->|Unknown state invokes onboarding| OStart
    AppModel -->|Known state continues flow| Next
```

## Architecture Responsibilities

- **Onboarding Graph**: Discovers an application state, generates smoke and flow hypotheses, and builds initial executable tests.
- **Cron Graph**: Selects stored tests, runs them continuously, captures evidence, and routes outcomes.
- **Discovery**: A reusable Playwright capability used by onboarding, healing, and verification. It returns structured page and state data rather than relying on an LLM to inspect the DOM.
- **Hypothesis Generator**: Converts the Application Model into candidate smoke and flow tests.
- **Builder**: Converts accepted hypotheses into Playwright test scripts.
- **Runner and Observer**: Execute tests and capture browser evidence without LLM-driven interaction.
- **Analyzer**: Emits one machine-readable verdict: `PASS`, `NEED_HEAL`, or `SUSPECTED_APP_FAILURE`.
- **Healer and Editor**: Use fresh discovery around a failed interaction, create a repair plan, update the test, and rerun it.
- **Verifier**: Independently performs fresh discovery and a focused smoke test before confirming an application bug.
- **Application Model**: Stores known screens, states, and discovered structure.
- **Test Repository**: Stores generated tests, metadata, status, execution history, and healing information.

## Execution Lifecycle

1. Onboarding discovers the initial application state.
2. Hypotheses are generated and converted into Playwright tests.
3. Tests are stored in the Test Repository.
4. Cron selects tests for continuous execution.
5. Runner executes and Observer captures evidence.
6. Analyzer returns `PASS`, `NEED_HEAL`, or `SUSPECTED_APP_FAILURE`.
7. Healing uses fresh discovery to repair and rerun invalid tests.
8. Verification uses fresh discovery plus a focused smoke test before reporting a bug.
9. Newly encountered states are compared with the Application Model; genuinely new states invoke onboarding.

## Current Repository Status

The repository currently contains a React/Vite client and a Python backend scaffold. The AI Testing Agent graphs, Playwright runtime, persistence layers, and API integration described above are proposal architecture and remain to be implemented.
