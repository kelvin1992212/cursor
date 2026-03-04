/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { channelLabel, formatDateTime } from "../lib/format";

const initialSchedule = {
  ai_schedule_start: "00:00",
  ai_schedule_end: "00:00",
  timezone: "Asia/Hong_Kong",
};

const initialIntegration = {
  phone_number_id: "",
  webhook_verify_token: "",
  whatsapp_access_token: "",
  openai_api_key: "",
  openai_model: "gpt-4o-mini",
  ai_provider: "rule_based",
};

export default function AISettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryChatroomId = Number(searchParams.get("chatroomId")) || null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [selectedChatroomId, setSelectedChatroomId] = useState(queryChatroomId);
  const [schedule, setSchedule] = useState(initialSchedule);
  const [integration, setIntegration] = useState(null);
  const [integrationForm, setIntegrationForm] = useState(initialIntegration);

  const selectedChatroom = useMemo(
    () => chatrooms.find((room) => room.id === selectedChatroomId) || null,
    [chatrooms, selectedChatroomId],
  );

  const fetchChatrooms = useCallback(async () => {
    setError("");
    try {
      const rows = await api.listChatrooms();
      setChatrooms(rows);
      if (!selectedChatroomId && rows.length > 0) {
        setSelectedChatroomId(rows[0].id);
      }
      return rows;
    } catch (fetchError) {
      setError(fetchError.message);
      return [];
    }
  }, [selectedChatroomId]);

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      const rows = await fetchChatrooms();
      if (queryChatroomId && rows.find((item) => item.id === queryChatroomId)) {
        setSelectedChatroomId(queryChatroomId);
      }
      setLoading(false);
    }
    bootstrap();
  }, [fetchChatrooms, queryChatroomId]);

  useEffect(() => {
    if (!selectedChatroom) return;
    setSchedule({
      ai_schedule_start: selectedChatroom.ai_schedule_start,
      ai_schedule_end: selectedChatroom.ai_schedule_end,
      timezone: selectedChatroom.timezone,
    });
    setSearchParams({ chatroomId: String(selectedChatroom.id) }, { replace: true });

    async function fetchIntegration() {
      try {
        const data = await api.getChatroomIntegration(selectedChatroom.id);
        setIntegration(data);
        setIntegrationForm({
          phone_number_id: data.phone_number_id || selectedChatroom.external_room_id || "",
          webhook_verify_token: "",
          whatsapp_access_token: "",
          openai_api_key: "",
          openai_model: data.openai_model || "gpt-4o-mini",
          ai_provider: data.ai_provider || "rule_based",
        });
      } catch (fetchError) {
        setError(fetchError.message);
      }
    }
    fetchIntegration();
  }, [selectedChatroom, setSearchParams]);

  async function refreshCurrent() {
    await fetchChatrooms();
  }

  async function handleToggle() {
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.updateChatroomAIStatus(selectedChatroom.id, !selectedChatroom.ai_enabled);
      await fetchChatrooms();
      setNotice(`AI ${selectedChatroom.ai_enabled ? "disabled" : "enabled"} for this chatroom.`);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handlePause() {
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.pauseChatroomAI(selectedChatroom.id);
      await fetchChatrooms();
      setNotice("AI paused for this chatroom.");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleScheduleUpdate(event) {
    event.preventDefault();
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.updateChatroomSchedule(
        selectedChatroom.id,
        schedule.ai_schedule_start,
        schedule.ai_schedule_end,
        schedule.timezone,
      );
      await fetchChatrooms();
      setNotice("Schedule updated.");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleIntegrationUpdate(event) {
    event.preventDefault();
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.updateChatroomIntegration(selectedChatroom.id, integrationForm);
      const [rows, nextIntegration] = await Promise.all([
        api.listChatrooms(),
        api.getChatroomIntegration(selectedChatroom.id),
      ]);
      setChatrooms(rows);
      setIntegration(nextIntegration);
      setIntegrationForm((previous) => ({
        ...previous,
        webhook_verify_token: "",
        whatsapp_access_token: "",
        openai_api_key: "",
      }));
      setNotice("Integration settings updated.");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <section className="page">
      <header className="page-header-row">
        <div>
          <h2>AI Settings</h2>
          <p className="muted">Each chatroom has its own AI switch and schedule.</p>
        </div>
        <button type="button" onClick={refreshCurrent}>
          Refresh
        </button>
      </header>

      {loading && <p className="notice">Loading...</p>}
      {notice && <p className="notice success">{notice}</p>}
      {error && <p className="notice error">{error}</p>}

      <section className="panel">
        <label>
          Select chatroom
          <select
            value={selectedChatroomId || ""}
            onChange={(event) => setSelectedChatroomId(Number(event.target.value))}
          >
            {chatrooms.length === 0 && <option value="">No chatrooms</option>}
            {chatrooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.name} ({channelLabel(room.channel)})
              </option>
            ))}
          </select>
        </label>

        {!selectedChatroom && <p className="muted">Select a room to configure AI.</p>}
        {selectedChatroom && (
          <>
            <div className="ai-toolbar">
              <p>
                <strong>Status:</strong> {selectedChatroom.ai_enabled ? "Enabled" : "Paused"}
              </p>
              <p>
                <strong>Current:</strong> {selectedChatroom.ai_schedule_start} - {selectedChatroom.ai_schedule_end} (
                {selectedChatroom.timezone})
              </p>
              <p>
                <strong>Updated:</strong> {formatDateTime(selectedChatroom.updated_at)}
              </p>
              <button type="button" onClick={handleToggle}>
                {selectedChatroom.ai_enabled ? "Disable AI" : "Enable AI"}
              </button>
              <button type="button" onClick={handlePause}>
                One-click Pause
              </button>
            </div>
            <form onSubmit={handleScheduleUpdate} className="form-grid">
              <label>
                Start time
                <input
                  type="time"
                  value={schedule.ai_schedule_start}
                  onChange={(event) =>
                    setSchedule((previous) => ({ ...previous, ai_schedule_start: event.target.value }))
                  }
                  required
                />
              </label>
              <label>
                End time
                <input
                  type="time"
                  value={schedule.ai_schedule_end}
                  onChange={(event) =>
                    setSchedule((previous) => ({ ...previous, ai_schedule_end: event.target.value }))
                  }
                  required
                />
              </label>
              <label>
                Timezone
                <input
                  value={schedule.timezone}
                  onChange={(event) => setSchedule((previous) => ({ ...previous, timezone: event.target.value }))}
                  required
                />
              </label>
              <button type="submit">Update schedule</button>
            </form>
            <section className="panel nested-panel">
              <h3>Integration Settings</h3>
              <p className="muted">
                Configure webhook token, WhatsApp phone ID/access token, and OpenAI key/model for this chatroom.
              </p>
              {integration && (
                <div className="integration-flags">
                  <p>
                    <strong>Webhook token:</strong> {integration.webhook_verify_token_set ? "configured" : "not set"}
                  </p>
                  <p>
                    <strong>WhatsApp access token:</strong>{" "}
                    {integration.whatsapp_access_token_set ? "configured" : "not set"}
                  </p>
                  <p>
                    <strong>OpenAI key:</strong> {integration.openai_api_key_set ? "configured" : "not set"}
                  </p>
                  <p>
                    <strong>AI provider:</strong> {integration.ai_provider}
                  </p>
                </div>
              )}
              <form onSubmit={handleIntegrationUpdate} className="form-grid">
                <label>
                  WhatsApp Phone Number ID
                  <input
                    value={integrationForm.phone_number_id}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, phone_number_id: event.target.value }))
                    }
                    placeholder="123456789012345"
                  />
                </label>
                <label>
                  Webhook Verify Token
                  <input
                    value={integrationForm.webhook_verify_token}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, webhook_verify_token: event.target.value }))
                    }
                    placeholder="set to configure webhook verify"
                  />
                </label>
                <label>
                  WhatsApp Access Token
                  <input
                    value={integrationForm.whatsapp_access_token}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, whatsapp_access_token: event.target.value }))
                    }
                    placeholder="set token used for outbound calls"
                  />
                </label>
                <label>
                  AI Provider
                  <select
                    value={integrationForm.ai_provider}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, ai_provider: event.target.value }))
                    }
                  >
                    <option value="rule_based">rule_based</option>
                    <option value="openai">openai</option>
                  </select>
                </label>
                <label>
                  OpenAI API Key
                  <input
                    value={integrationForm.openai_api_key}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, openai_api_key: event.target.value }))
                    }
                    placeholder="required when AI provider=openai"
                  />
                </label>
                <label>
                  OpenAI Model
                  <input
                    value={integrationForm.openai_model}
                    onChange={(event) =>
                      setIntegrationForm((previous) => ({ ...previous, openai_model: event.target.value }))
                    }
                    placeholder="gpt-4o-mini"
                  />
                </label>
                <button type="submit">Update integration</button>
              </form>
              {selectedChatroom.channel === "whatsapp" && (
                <p className="muted">
                  Verify URL:
                  <code>
                    {` /omni/webhooks/whatsapp/${integrationForm.phone_number_id || selectedChatroom.external_room_id}`}
                  </code>
                </p>
              )}
            </section>
          </>
        )}
      </section>
    </section>
  );
}
