import { useEffect, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function App() {
  const [options, setOptions] = useState(null);
  const [payloadKey, setPayloadKey] = useState("salesforce_sso");
  const [datasetKey, setDatasetKey] = useState("it_mim");
  const [workflow, setWorkflow] = useState(null);
  const [selectedActionId, setSelectedActionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/options`)
      .then((response) => {
        if (!response.ok) throw new Error("Failed to load API options");
        return response.json();
      })
      .then(setOptions)
      .catch((err) => setError(err.message));
  }, []);

  async function createWorkflow() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/workflows`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          payload_key: payloadKey,
          dataset_key: datasetKey,
        }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || "Failed to create workflow");
      }

      const body = await response.json();
      setWorkflow(body);

      const actions = body?.action_plan?.proposed_actions || [];
      setSelectedActionId(actions[0]?.action_id || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function approveAction() {
    if (!workflow || !selectedActionId) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workflows/${workflow.workflow_id}/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action_id: selectedActionId,
          }),
        }
      );

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || "Failed to approve action");
      }

      const body = await response.json();
      setWorkflow(body);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const actions = workflow?.action_plan?.proposed_actions || [];
  const succeeded =
    workflow?.execution?.results?.filter((result) => result.status === "succeeded") || [];

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">MIM Incident Intelligence</p>
          <h1>Approval-gated incident workflow demo</h1>
          <p>
            Select a payload and memory dataset, generate a KBA/DIP-backed action
            plan, approve one action, and inspect execution and validation.
          </p>
        </div>
        <div className="statusPill">API: {options ? "connected" : "loading"}</div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="card controls">
        <label>
          Payload
          <select value={payloadKey} onChange={(e) => setPayloadKey(e.target.value)}>
            {options &&
              Object.keys(options.payloads).map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
          </select>
        </label>

        <label>
          Dataset / memory
          <select value={datasetKey} onChange={(e) => setDatasetKey(e.target.value)}>
            {options &&
              Object.keys(options.datasets).map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
          </select>
        </label>

        <button onClick={createWorkflow} disabled={loading || !options}>
          {loading ? "Running..." : "Create workflow"}
        </button>
      </section>

      {workflow && (
        <>
          <section className="grid">
            <div className="card">
              <h2>Workflow</h2>
              <p><strong>ID:</strong> {workflow.workflow_id}</p>
              <p><strong>Status:</strong> {workflow.status}</p>
              <p><strong>Service:</strong> {workflow.incident?.service}</p>
              <p><strong>Priority:</strong> {workflow.incident?.priority}</p>
            </div>

            <div className="card">
              <h2>Analysis</h2>
              <p><strong>MIM:</strong> {workflow.analysis?.mim_classification}</p>
              <p><strong>Confidence:</strong> {workflow.analysis?.mim_confidence}</p>
              <p><strong>KBA:</strong> {workflow.analysis?.recommended_kba_id || "None"}</p>
              <p><strong>Resolver:</strong> {workflow.analysis?.recommended_resolver_group || "None"}</p>
            </div>

            <div className="card">
              <h2>DIP</h2>
              {workflow.context?.matched_dips?.length ? (
                <>
                  <p><strong>ID:</strong> {workflow.context.matched_dips[0].dip_id}</p>
                  <p><strong>Title:</strong> {workflow.context.matched_dips[0].title}</p>
                  <p><strong>Risk:</strong> {workflow.context.matched_dips[0].risk_level}</p>
                </>
              ) : (
                <p>No matched DIP. Manual review required.</p>
              )}
            </div>
          </section>

          <section className="card">
            <h2>Proposed actions</h2>

            {actions.length ? (
              <>
                <div className="actions">
                  {actions.map((action) => (
                    <div key={action.action_id} className="action">
                      <div>
                        <strong>{action.action_id}</strong>
                        <p>{action.description}</p>
                        <small>
                          {action.gke_namespace || "no namespace"} ·{" "}
                          {action.ansible_playbook || "no playbook"}
                        </small>
                      </div>
                      <span>{action.approval_status}</span>
                    </div>
                  ))}
                </div>

                <div className="approveRow">
                  <select
                    value={selectedActionId}
                    onChange={(e) => setSelectedActionId(e.target.value)}
                  >
                    {actions.map((action) => (
                      <option key={action.action_id} value={action.action_id}>
                        {action.action_id}
                      </option>
                    ))}
                  </select>

                  <button onClick={approveAction} disabled={loading || !selectedActionId}>
                    Approve and execute
                  </button>
                </div>
              </>
            ) : (
              <p>{workflow.action_plan?.summary}</p>
            )}
          </section>

          <section className="grid two">
            <div className="card">
              <h2>Execution</h2>
              <p><strong>Approved:</strong> {workflow.execution?.approved_action_ids?.join(", ") || "None"}</p>
              <p><strong>Succeeded:</strong> {succeeded.length}</p>
              <pre>{JSON.stringify(workflow.execution?.results || [], null, 2)}</pre>
            </div>

            <div className="card">
              <h2>Validation</h2>
              <p><strong>Status:</strong> {workflow.validation?.status}</p>
              <pre>{JSON.stringify(workflow.validation?.evidence || [], null, 2)}</pre>
            </div>
          </section>

          <section className="card">
            <h2>Full workflow state</h2>
            <pre>{JSON.stringify(workflow, null, 2)}</pre>
          </section>
        </>
      )}
    </main>
  );
}

export default App;
