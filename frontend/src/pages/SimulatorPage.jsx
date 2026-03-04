/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { channelLabel } from "../lib/format";

const defaultForm = {
  channel: "whatsapp",
  chatroom_external_id: "",
  contact_id: "",
  contact_name: "",
  text: "",
};

export default function SimulatorPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [selectedChatroomId, setSelectedChatroomId] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [lastResult, setLastResult] = useState(null);

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
      await fetchChatrooms();
      setLoading(false);
    }
    bootstrap();
  }, [fetchChatrooms]);

  useEffect(() => {
    if (!selectedChatroom) return;
    setForm((previous) => ({
      ...previous,
      channel: selectedChatroom.channel,
      chatroom_external_id: selectedChatroom.external_room_id,
    }));
  }, [selectedChatroom]);

  async function handleSimulate(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const result = await api.simulateIncoming(form);
      setLastResult(result);
      setNotice(`Inbound simulated for ${result.channel}. AI replied: ${result.ai_replied ? "yes" : "no"}`);
      setForm((previous) => ({ ...previous, text: "" }));
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <section className="page">
      <header className="page-header-row">
        <div>
          <h2>Webhook Simulator</h2>
          <p className="muted">Create inbound messages for any chatroom/channel.</p>
        </div>
      </header>

      {loading && <p className="notice">Loading...</p>}
      {notice && <p className="notice success">{notice}</p>}
      {error && <p className="notice error">{error}</p>}

      <section className="panel">
        <form onSubmit={handleSimulate} className="form-grid">
          <label>
            Choose chatroom
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
          <label>
            Channel
            <input value={form.channel} readOnly />
          </label>
          <label>
            Chatroom external ID
            <input
              value={form.chatroom_external_id}
              onChange={(event) => setForm((previous) => ({ ...previous, chatroom_external_id: event.target.value }))}
              required
            />
          </label>
          <label>
            Contact ID
            <input
              value={form.contact_id}
              onChange={(event) => setForm((previous) => ({ ...previous, contact_id: event.target.value }))}
              required
            />
          </label>
          <label>
            Contact name
            <input
              value={form.contact_name}
              onChange={(event) => setForm((previous) => ({ ...previous, contact_name: event.target.value }))}
            />
          </label>
          <label className="wide-field">
            Message
            <input
              value={form.text}
              onChange={(event) => setForm((previous) => ({ ...previous, text: event.target.value }))}
              required
            />
          </label>
          <button type="submit">Simulate inbound</button>
        </form>
      </section>

      {lastResult && (
        <section className="panel">
          <h3>Latest Result</h3>
          <div className="result-grid">
            <p>
              <strong>Chatroom ID:</strong> {lastResult.chatroom_id}
            </p>
            <p>
              <strong>Thread ID:</strong> {lastResult.thread_id}
            </p>
            <p>
              <strong>AI Replied:</strong> {lastResult.ai_replied ? "Yes" : "No"}
            </p>
            <p>
              <strong>Reply text:</strong> {lastResult.reply_text || "-"}
            </p>
          </div>
          <div className="row">
            <Link to={`/inbox/${lastResult.chatroom_id}`}>Open chatroom inbox</Link>
            <Link to={`/ai-settings?chatroomId=${lastResult.chatroom_id}`}>Open AI settings</Link>
          </div>
        </section>
      )}
    </section>
  );
}
