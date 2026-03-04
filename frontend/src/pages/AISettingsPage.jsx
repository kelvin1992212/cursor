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

export default function AISettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryChatroomId = Number(searchParams.get("chatroomId")) || null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [selectedChatroomId, setSelectedChatroomId] = useState(queryChatroomId);
  const [schedule, setSchedule] = useState(initialSchedule);

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
          </>
        )}
      </section>
    </section>
  );
}
