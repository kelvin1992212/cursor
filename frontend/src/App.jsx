import { useCallback, useEffect, useMemo, useState } from "react";
import { api, apiBaseUrl } from "./api";
import "./App.css";

const defaultSchedule = {
  schedule_start: "20:00",
  schedule_end: "09:00",
  timezone: "Asia/Hong_Kong",
};

const defaultLeadFilters = {
  tag: "",
  property_code: "",
  intent_stage: "",
  from_date: "",
  to_date: "",
};

const defaultBookingForm = {
  phone: "",
  scheduled_at: "",
  property_code: "",
  notes: "",
  channel: "whatsapp",
};

const defaultSimulateForm = {
  channel: "whatsapp",
  phone: "",
  name: "",
  text: "",
};

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function App() {
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [aiStatus, setAiStatus] = useState(null);
  const [scheduleForm, setScheduleForm] = useState(defaultSchedule);

  const [agents, setAgents] = useState([]);
  const [newAgent, setNewAgent] = useState({
    name: "",
    phone: "",
    specialties: "",
    is_active: true,
  });

  const [leadFilters, setLeadFilters] = useState(defaultLeadFilters);
  const [leads, setLeads] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState("");
  const [customerDetail, setCustomerDetail] = useState(null);
  const [reports, setReports] = useState([]);

  const [tagInput, setTagInput] = useState("");
  const [feedbackForm, setFeedbackForm] = useState({
    phone: "",
    label: "correct",
    note: "",
  });

  const [bookings, setBookings] = useState([]);
  const [bookingForm, setBookingForm] = useState(defaultBookingForm);
  const [simulateForm, setSimulateForm] = useState(defaultSimulateForm);

  const currentLead = useMemo(() => leads.find((item) => item.phone === selectedPhone), [leads, selectedPhone]);

  const refreshDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [status, agentRows, bookingRows, leadRows] = await Promise.all([
        api.getAIStatus(),
        api.listAgents(),
        api.listBookings(),
        api.listLeads(defaultLeadFilters),
      ]);
      setAiStatus(status);
      setScheduleForm({
        schedule_start: status.schedule_start,
        schedule_end: status.schedule_end,
        timezone: status.timezone,
      });
      setAgents(agentRows);
      setBookings(bookingRows);
      setLeads(leadRows);
      if (leadRows.length > 0) {
        setSelectedPhone((previous) => previous || leadRows[0].phone);
      }
    } catch (fetchError) {
      setError(fetchError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshCustomer = useCallback(async (phone) => {
    try {
      const [detail, leadReports] = await Promise.all([api.getCustomer(phone), api.listReports(phone)]);
      setCustomerDetail(detail);
      setReports(leadReports);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }, []);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    if (!selectedPhone) {
      setCustomerDetail(null);
      setReports([]);
      return;
    }
    refreshCustomer(selectedPhone);
    setFeedbackForm((previous) => ({ ...previous, phone: selectedPhone }));
    setBookingForm((previous) => ({ ...previous, phone: selectedPhone }));
    setSimulateForm((previous) => ({ ...previous, phone: selectedPhone }));
  }, [refreshCustomer, selectedPhone]);

  async function handleLeadSearch(event) {
    event.preventDefault();
    setError("");
    try {
      const rows = await api.listLeads(leadFilters);
      setLeads(rows);
      if (!rows.find((item) => item.phone === selectedPhone)) {
        setSelectedPhone(rows[0]?.phone || "");
      }
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleAIPause() {
    setError("");
    try {
      const next = await api.pauseAI();
      setAiStatus(next);
      setMessage("AI 已暫停。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleAIToggle() {
    if (!aiStatus) return;
    setError("");
    try {
      const next = await api.updateAIStatus(!aiStatus.enabled);
      setAiStatus(next);
      setMessage(`AI 已${next.enabled ? "啟用" : "關閉"}。`);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleScheduleUpdate(event) {
    event.preventDefault();
    setError("");
    try {
      const next = await api.updateAISchedule(
        scheduleForm.schedule_start,
        scheduleForm.schedule_end,
        scheduleForm.timezone,
      );
      setAiStatus(next);
      setMessage("AI 工作時間已更新。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleCreateAgent(event) {
    event.preventDefault();
    setError("");
    try {
      await api.createAgent(newAgent);
      setNewAgent({ name: "", phone: "", specialties: "", is_active: true });
      setAgents(await api.listAgents());
      setMessage("Agent 已新增。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleAddTag(event) {
    event.preventDefault();
    if (!selectedPhone || !tagInput.trim()) return;
    setError("");
    const tags = tagInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (tags.length === 0) return;
    try {
      const updated = await api.addCustomerTags(selectedPhone, tags);
      setCustomerDetail(updated);
      setTagInput("");
      setLeads(await api.listLeads(leadFilters));
      setMessage("Tag 已更新。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleRemoveTag(tagName) {
    if (!selectedPhone) return;
    setError("");
    try {
      const updated = await api.removeCustomerTag(selectedPhone, tagName);
      setCustomerDetail(updated);
      setLeads(await api.listLeads(leadFilters));
      setMessage(`已移除標籤: ${tagName}`);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleCreateBooking(event) {
    event.preventDefault();
    setError("");
    try {
      const isoValue = new Date(bookingForm.scheduled_at).toISOString();
      await api.createBooking({
        ...bookingForm,
        scheduled_at: isoValue,
      });
      setBookings(await api.listBookings());
      setBookingForm((previous) => ({
        ...defaultBookingForm,
        phone: previous.phone,
      }));
      setMessage("預約已建立。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleSubmitFeedback(event) {
    event.preventDefault();
    if (!feedbackForm.phone) {
      setError("請先選擇客戶。");
      return;
    }
    setError("");
    try {
      await api.createFeedback(feedbackForm);
      setFeedbackForm((previous) => ({ ...previous, note: "" }));
      setMessage("Feedback 已提交。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleSimulateMessage(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const result = await api.simulateIncoming(simulateForm);
      setMessage(
        `已送出模擬訊息，系統模式：${result.mode}${result.assigned_agent ? `，分派 ${result.assigned_agent}` : ""}`,
      );
      const leadRows = await api.listLeads(leadFilters);
      setLeads(leadRows);
      if (simulateForm.phone) {
        setSelectedPhone(simulateForm.phone);
        await refreshCustomer(simulateForm.phone);
      }
      setBookings(await api.listBookings());
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <main className="layout">
      <header className="page-header">
        <div>
          <h1>House 88 AI Lead Dashboard</h1>
          <p className="subtext">Frontend connected to: {apiBaseUrl}</p>
        </div>
        <button type="button" onClick={refreshDashboard}>
          Refresh
        </button>
      </header>

      {loading && <p className="notice">載入中...</p>}
      {message && <p className="notice success">{message}</p>}
      {error && <p className="notice error">{error}</p>}

      <section className="panel">
        <h2>AI Control Center</h2>
        <div className="row row-wrap">
          <p>
            <strong>Status:</strong> {aiStatus?.enabled ? "Enabled" : "Paused"}
          </p>
          <p>
            <strong>Schedule:</strong> {aiStatus?.schedule_start || "-"} - {aiStatus?.schedule_end || "-"} (
            {aiStatus?.timezone || "-"})
          </p>
          <button type="button" onClick={handleAIToggle} disabled={!aiStatus}>
            {aiStatus?.enabled ? "Disable AI" : "Enable AI"}
          </button>
          <button type="button" onClick={handleAIPause}>
            One-click Pause
          </button>
        </div>
        <form onSubmit={handleScheduleUpdate} className="row row-wrap form-grid">
          <label>
            Start
            <input
              type="time"
              value={scheduleForm.schedule_start}
              onChange={(event) =>
                setScheduleForm((previous) => ({ ...previous, schedule_start: event.target.value }))
              }
              required
            />
          </label>
          <label>
            End
            <input
              type="time"
              value={scheduleForm.schedule_end}
              onChange={(event) => setScheduleForm((previous) => ({ ...previous, schedule_end: event.target.value }))}
              required
            />
          </label>
          <label>
            Timezone
            <input
              value={scheduleForm.timezone}
              onChange={(event) => setScheduleForm((previous) => ({ ...previous, timezone: event.target.value }))}
              required
            />
          </label>
          <button type="submit">Update Schedule</button>
        </form>
      </section>

      <section className="panel">
        <h2>Webhook Simulator</h2>
        <form onSubmit={handleSimulateMessage} className="row row-wrap form-grid">
          <label>
            Channel
            <select
              value={simulateForm.channel}
              onChange={(event) => setSimulateForm((previous) => ({ ...previous, channel: event.target.value }))}
            >
              <option value="whatsapp">WhatsApp</option>
              <option value="wechat">WeChat</option>
            </select>
          </label>
          <label>
            Phone
            <input
              value={simulateForm.phone}
              onChange={(event) => setSimulateForm((previous) => ({ ...previous, phone: event.target.value }))}
              placeholder="+85260000000"
              required
            />
          </label>
          <label>
            Name
            <input
              value={simulateForm.name}
              onChange={(event) => setSimulateForm((previous) => ({ ...previous, name: event.target.value }))}
              placeholder="Client name"
            />
          </label>
          <label className="wide-field">
            Message
            <input
              value={simulateForm.text}
              onChange={(event) => setSimulateForm((previous) => ({ ...previous, text: event.target.value }))}
              placeholder="例如：我想同真人傾，想即時報價"
              required
            />
          </label>
          <button type="submit">Send Simulated Inbound</button>
        </form>
      </section>

      <section className="two-column">
        <div className="panel">
          <h2>Leads</h2>
          <form onSubmit={handleLeadSearch} className="row row-wrap compact-form">
            <input
              placeholder="Tag"
              value={leadFilters.tag}
              onChange={(event) => setLeadFilters((previous) => ({ ...previous, tag: event.target.value }))}
            />
            <input
              placeholder="Property Code"
              value={leadFilters.property_code}
              onChange={(event) =>
                setLeadFilters((previous) => ({ ...previous, property_code: event.target.value }))
              }
            />
            <input
              placeholder="Intent Stage"
              value={leadFilters.intent_stage}
              onChange={(event) =>
                setLeadFilters((previous) => ({ ...previous, intent_stage: event.target.value }))
              }
            />
            <label>
              From
              <input
                type="date"
                value={leadFilters.from_date}
                onChange={(event) =>
                  setLeadFilters((previous) => ({ ...previous, from_date: event.target.value }))
                }
              />
            </label>
            <label>
              To
              <input
                type="date"
                value={leadFilters.to_date}
                onChange={(event) => setLeadFilters((previous) => ({ ...previous, to_date: event.target.value }))}
              />
            </label>
            <button type="submit">Search</button>
          </form>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Phone</th>
                  <th>Name</th>
                  <th>Intent</th>
                  <th>Tags</th>
                  <th>Last Message</th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 && (
                  <tr>
                    <td colSpan="5">No leads found.</td>
                  </tr>
                )}
                {leads.map((lead) => (
                  <tr
                    key={lead.phone}
                    className={lead.phone === selectedPhone ? "selected-row" : ""}
                    onClick={() => setSelectedPhone(lead.phone)}
                  >
                    <td>{lead.phone}</td>
                    <td>{lead.name || "-"}</td>
                    <td>{lead.intent_stage}</td>
                    <td>{lead.tags.join(", ") || "-"}</td>
                    <td>{lead.last_message || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <h2>Customer Detail</h2>
          {!selectedPhone && <p>Select a lead to view detail.</p>}
          {selectedPhone && (
            <>
              <p>
                <strong>Phone:</strong> {customerDetail?.phone || selectedPhone}
              </p>
              <p>
                <strong>Name:</strong> {customerDetail?.name || currentLead?.name || "-"}
              </p>
              <p>
                <strong>Intent:</strong> {customerDetail?.intent_stage || currentLead?.intent_stage || "-"}
              </p>
              <p>
                <strong>Follow-up:</strong> {customerDetail?.follow_up_status || currentLead?.follow_up_status || "-"}
              </p>
              <p>
                <strong>Budget:</strong>{" "}
                {customerDetail?.budget_min || customerDetail?.budget_max
                  ? `${customerDetail?.budget_min || "-"} ~ ${customerDetail?.budget_max || "-"}`
                  : "-"}
              </p>

              <div className="tag-list">
                {(customerDetail?.tags || []).map((tag) => (
                  <span key={tag} className="tag-pill">
                    {tag}
                    <button type="button" onClick={() => handleRemoveTag(tag)}>
                      ×
                    </button>
                  </span>
                ))}
              </div>

              <form onSubmit={handleAddTag} className="row">
                <input
                  value={tagInput}
                  onChange={(event) => setTagInput(event.target.value)}
                  placeholder="Add tag, or comma-separated tags"
                />
                <button type="submit">Add Tag</button>
              </form>
            </>
          )}
        </div>
      </section>

      <section className="two-column">
        <div className="panel">
          <h2>Booking Management</h2>
          <form onSubmit={handleCreateBooking} className="row row-wrap form-grid">
            <label>
              Customer Phone
              <input
                required
                value={bookingForm.phone}
                onChange={(event) => setBookingForm((previous) => ({ ...previous, phone: event.target.value }))}
              />
            </label>
            <label>
              Time
              <input
                required
                type="datetime-local"
                value={bookingForm.scheduled_at}
                onChange={(event) =>
                  setBookingForm((previous) => ({ ...previous, scheduled_at: event.target.value }))
                }
              />
            </label>
            <label>
              Property Code
              <input
                value={bookingForm.property_code}
                onChange={(event) =>
                  setBookingForm((previous) => ({ ...previous, property_code: event.target.value }))
                }
              />
            </label>
            <label>
              Channel
              <select
                value={bookingForm.channel}
                onChange={(event) => setBookingForm((previous) => ({ ...previous, channel: event.target.value }))}
              >
                <option value="whatsapp">WhatsApp</option>
                <option value="wechat">WeChat</option>
              </select>
            </label>
            <label className="wide-field">
              Notes
              <input
                value={bookingForm.notes}
                onChange={(event) => setBookingForm((previous) => ({ ...previous, notes: event.target.value }))}
              />
            </label>
            <button type="submit">Create Booking</button>
          </form>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Agent</th>
                  <th>Property</th>
                </tr>
              </thead>
              <tbody>
                {bookings.length === 0 && (
                  <tr>
                    <td colSpan="5">No bookings yet.</td>
                  </tr>
                )}
                {bookings.map((booking) => (
                  <tr key={booking.id}>
                    <td>{formatDateTime(booking.scheduled_at)}</td>
                    <td>{booking.customer_phone}</td>
                    <td>{booking.status}</td>
                    <td>{booking.agent_name || "-"}</td>
                    <td>{booking.property_code || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <h2>Lead Reports & AI Feedback</h2>
          {!selectedPhone && <p>Select a lead to view reports and submit feedback.</p>}
          {selectedPhone && (
            <>
              <p>
                <strong>Reports for:</strong> {selectedPhone}
              </p>
              <ul className="report-list">
                {reports.length === 0 && <li>No reports yet.</li>}
                {reports.map((report) => (
                  <li key={report.id}>
                    <p>
                      <strong>#{report.id}</strong> at {formatDateTime(report.created_at)}{" "}
                      {report.agent_name ? `(Agent: ${report.agent_name})` : ""}
                    </p>
                    <pre>{JSON.stringify(report.summary_json, null, 2)}</pre>
                  </li>
                ))}
              </ul>
              <form onSubmit={handleSubmitFeedback} className="row row-wrap">
                <input value={feedbackForm.phone} readOnly />
                <select
                  value={feedbackForm.label}
                  onChange={(event) => setFeedbackForm((previous) => ({ ...previous, label: event.target.value }))}
                >
                  <option value="correct">correct</option>
                  <option value="improve">improve</option>
                </select>
                <input
                  value={feedbackForm.note}
                  onChange={(event) => setFeedbackForm((previous) => ({ ...previous, note: event.target.value }))}
                  placeholder="Feedback note"
                />
                <button type="submit">Submit Feedback</button>
              </form>
            </>
          )}
        </div>
      </section>

      <section className="panel">
        <h2>Agents</h2>
        <form onSubmit={handleCreateAgent} className="row row-wrap form-grid">
          <label>
            Name
            <input
              required
              value={newAgent.name}
              onChange={(event) => setNewAgent((previous) => ({ ...previous, name: event.target.value }))}
            />
          </label>
          <label>
            Phone
            <input
              required
              value={newAgent.phone}
              onChange={(event) => setNewAgent((previous) => ({ ...previous, phone: event.target.value }))}
            />
          </label>
          <label>
            Specialties
            <input
              value={newAgent.specialties}
              onChange={(event) => setNewAgent((previous) => ({ ...previous, specialties: event.target.value }))}
            />
          </label>
          <label>
            Active
            <select
              value={newAgent.is_active ? "true" : "false"}
              onChange={(event) =>
                setNewAgent((previous) => ({ ...previous, is_active: event.target.value === "true" }))
              }
            >
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <button type="submit">Add Agent</button>
        </form>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Specialties</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>{agent.id}</td>
                  <td>{agent.name}</td>
                  <td>{agent.phone}</td>
                  <td>{agent.specialties || "-"}</td>
                  <td>{String(agent.is_active)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default App;
