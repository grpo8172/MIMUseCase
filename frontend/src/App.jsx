import { useEffect, useState } from "react";
import "./App.css";

export function LiveExecutionControls() {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");

  async function updateCapacity(action) {
    setStatus("requesting");
    setMessage("");

    try {
      const response = await fetch(`/api/execution/${action}`, {
        method: "POST",
      });

      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail ?? "Request failed");
      }

      setStatus(body.capacity_status);
      setMessage(
        action === "enable"
          ? "Live remediation capacity requested."
          : "Scale-down requested."
      );
    } catch (error) {
      setStatus("error");
      setMessage(
        error instanceof Error ? error.message : "Unexpected error"
      );
    }
  }

  return (
    <section>
      <h3>Controlled Live Execution</h3>

      <button
        type="button"
        disabled={status === "requesting"}
        onClick={() => updateCapacity("enable")}
      >
        Enable live remediation
      </button>

      <button
        type="button"
        disabled={status === "requesting"}
        onClick={() => updateCapacity("disable")}
      >
        Disable live remediation
      </button>

      {message && <p>{message}</p>}
    </section>
  );
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const DEFAULT_MANUAL_PAYLOAD = {
  incident_id: "INC-MANUAL-001",
  service: "Salesforce",
  short_description: "Users unable to login",
  description: "SSO redirect loop after SAML certificate change",
  severity: "SEV1",
  priority: "P1",
  assignment_group: "Unknown",
};

function App() {
  const [options, setOptions] = useState(null);
  const [inputMode, setInputMode] = useState("sample");
  const [payloadKey, setPayloadKey] = useState("salesforce_sso");
  const [datasetKey, setDatasetKey] = useState("it_mim");
  const [manualPayload, setManualPayload] = useState(
    JSON.stringify(DEFAULT_MANUAL_PAYLOAD, null, 2)
  );

  const [workflow, setWorkflow] = useState(null);
  const [selectedActionId, setSelectedActionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/options`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load API options");
        }

        return response.json();
      })
      .then(setOptions)
      .catch((err) => setError(err.message));
  }, []);

  async function createWorkflow() {
    setLoading(true);
    setError("");

    try {
      const requestBody =
        inputMode === "manual"
          ? {
              payload: JSON.parse(manualPayload),
              dataset_key: datasetKey,
            }
          : {
              payload_key: payloadKey,
              dataset_key: datasetKey,
            };

      const response = await fetch(`${API_BASE_URL}/api/workflows`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || "Failed to create workflow");
      }

      const body = await response.json();
      const actions = body?.action_plan?.proposed_actions || [];

      setWorkflow(body);
      setSelectedActionId(actions[0]?.action_id || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function approveAction() {
    if (!workflow || !selectedActionId) {
      return;
    }

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

      setWorkflow(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const actions = workflow?.action_plan?.proposed_actions || [];
  const memoryRecords = workflow?.context?.matched_change_records || [];
  const succeeded =
    workflow?.execution?.results?.filter(
      (result) => result.status === "succeeded"
    ) || [];

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">MIM Incident Intelligence</p>
          <h1>Approval-gated incident workflow demo</h1>
          <p>
            Submit a sample or manual incident payload, retrieve operational
            memory, generate a KBA/DIP-backed plan, and execute only an approved
            action.
          </p>
        </div>

        <div className="statusPill">
          API: {options ? "connected" : "loading"}
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="card controls">
        <label>
          Input source
          <select
            value={inputMode}
            onChange={(event) => setInputMode(event.target.value)}
          >
            <option value="sample">Sample fixture</option>
            <option value="manual">Paste manual JSON payload</option>
          </select>
        </label>

        {inputMode === "sample" && (
          <label>
            Payload
            <select
              value={payloadKey}
              onChange={(event) => setPayloadKey(event.target.value)}
            >
              {options &&
                Object.keys(options.payloads).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
            </select>
          </label>
        )}

        <label>
          Dataset / memory
          <select
            value={datasetKey}
            onChange={(event) => setDatasetKey(event.target.value)}
          >
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

      {inputMode === "manual" && (
        <section className="card">
          <h2>Manual incident payload</h2>
          <p>
            Paste a ServiceNow-style, Dynatrace-style, or manually constructed
            incident payload.
          </p>

          <textarea
            className="payloadEditor"
            value={manualPayload}
            onChange={(event) => setManualPayload(event.target.value)}
            rows={16}
            spellCheck="false"
          />
        </section>
      )}

      {workflow && (
        <>
          <section className="grid">
            <div className="card">
              <h2>Workflow</h2>
              <p>
                <strong>ID:</strong> {workflow.workflow_id}
              </p>
              <p>
                <strong>Status:</strong> {workflow.status}
              </p>
              <p>
                <strong>Service:</strong> {workflow.incident?.service}
              </p>
              <p>
                <strong>Priority:</strong> {workflow.incident?.priority}
              </p>
            </div>

            <div className="card">
              <h2>Analysis</h2>
              <p>
                <strong>MIM:</strong>{" "}
                {workflow.analysis?.mim_classification || "None"}
              </p>
              <p>
                <strong>Confidence:</strong>{" "}
                {workflow.analysis?.mim_confidence ?? "None"}
              </p>
              <p>
                <strong>KBA:</strong>{" "}
                {workflow.analysis?.recommended_kba_id || "None"}
              </p>
              <p>
                <strong>Resolver:</strong>{" "}
                {workflow.analysis?.recommended_resolver_group || "None"}
              </p>
            </div>

            <div className="card">
              <h2>DIP</h2>
              {workflow.context?.matched_dips?.length ? (
                <>
                  <p>
                    <strong>ID:</strong>{" "}
                    {workflow.context.matched_dips[0].dip_id}
                  </p>
                  <p>
                    <strong>Title:</strong>{" "}
                    {workflow.context.matched_dips[0].title}
                  </p>
                  <p>
                    <strong>Risk:</strong>{" "}
                    {workflow.context.matched_dips[0].risk_level}
                  </p>
                </>
              ) : (
                <p>No matched DIP. Manual review required.</p>
              )}
            </div>
          </section>

          <section className="card">
            <h2>Operational memory</h2>

            {memoryRecords.length ? (
              <>
                <p>
                  <strong>Source:</strong>{" "}
                  {memoryRecords[0].source || "unknown"}
                </p>
                <p>
                  <strong>Similar incidents:</strong>{" "}
                  {memoryRecords[0].similar_incident_count ?? 0}
                </p>

                <pre>
                  {JSON.stringify(
                    memoryRecords[0].similar_incidents || [],
                    null,
                    2
                  )}
                </pre>
              </>
            ) : (
              <p>No MongoDB MCP operational-memory records retrieved.</p>
            )}
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
                    onChange={(event) =>
                      setSelectedActionId(event.target.value)
                    }
                  >
                    {actions.map((action) => (
                      <option key={action.action_id} value={action.action_id}>
                        {action.action_id}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={approveAction}
                    disabled={loading || !selectedActionId}
                  >
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
              <p>
                <strong>Approved:</strong>{" "}
                {workflow.execution?.approved_action_ids?.join(", ") || "None"}
              </p>
              <p>
                <strong>Succeeded:</strong> {succeeded.length}
              </p>
              <pre>
                {JSON.stringify(workflow.execution?.results || [], null, 2)}
              </pre>
            </div>

            <div className="card">
              <h2>Validation</h2>
              <p>
                <strong>Status:</strong> {workflow.validation?.status}
              </p>
              <pre>
                {JSON.stringify(workflow.validation?.evidence || [], null, 2)}
              </pre>
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

