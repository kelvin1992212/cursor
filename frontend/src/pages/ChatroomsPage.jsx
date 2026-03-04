import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { CHANNEL_OPTIONS } from "../lib/constants";
import { channelLabel, formatDateTime } from "../lib/format";

const initialForm = {
  name: "",
  channel: "whatsapp",
  external_room_id: "",
};

export default function ChatroomsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [form, setForm] = useState(initialForm);

  const fetchChatrooms = useCallback(async () => {
    setError("");
    try {
      const rows = await api.listChatrooms(channelFilter ? { channel: channelFilter } : undefined);
      setChatrooms(rows);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }, [channelFilter]);

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      await fetchChatrooms();
      setLoading(false);
    }
    bootstrap();
  }, [fetchChatrooms]);

  const totals = useMemo(() => {
    const counts = { whatsapp: 0, wechat: 0, facebook: 0, instagram: 0, all: chatrooms.length };
    chatrooms.forEach((room) => {
      if (counts[room.channel] !== undefined) {
        counts[room.channel] += 1;
      }
    });
    return counts;
  }, [chatrooms]);

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api.createChatroom({
        name: form.name,
        channel: form.channel,
        external_room_id: form.external_room_id,
        ai_enabled: true,
        ai_schedule_start: "00:00",
        ai_schedule_end: "00:00",
        timezone: "Asia/Hong_Kong",
      });
      setForm(initialForm);
      await fetchChatrooms();
      setNotice("Chatroom created.");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <section className="page">
      <header className="page-header-row">
        <div>
          <h2>Chatrooms</h2>
          <p className="muted">Manage channel accounts/pages and room IDs.</p>
        </div>
        <button type="button" onClick={fetchChatrooms}>
          Refresh
        </button>
      </header>

      {loading && <p className="notice">Loading...</p>}
      {notice && <p className="notice success">{notice}</p>}
      {error && <p className="notice error">{error}</p>}

      <div className="stats-grid">
        <article className="stat-card">
          <p className="stat-number">{totals.all}</p>
          <p className="stat-label">Total rooms</p>
        </article>
        {CHANNEL_OPTIONS.map((channel) => (
          <article key={channel} className="stat-card">
            <p className="stat-number">{totals[channel]}</p>
            <p className="stat-label">{channelLabel(channel)}</p>
          </article>
        ))}
      </div>

      <section className="panel">
        <h3>Create New Chatroom</h3>
        <form onSubmit={handleCreate} className="form-grid">
          <label>
            Name
            <input
              value={form.name}
              onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))}
              required
            />
          </label>
          <label>
            Channel
            <select
              value={form.channel}
              onChange={(event) => setForm((previous) => ({ ...previous, channel: event.target.value }))}
            >
              {CHANNEL_OPTIONS.map((channel) => (
                <option key={channel} value={channel}>
                  {channelLabel(channel)}
                </option>
              ))}
            </select>
          </label>
          <label>
            External Room ID
            <input
              value={form.external_room_id}
              onChange={(event) => setForm((previous) => ({ ...previous, external_room_id: event.target.value }))}
              placeholder="e.g. phone_number_id/page_id"
              required
            />
          </label>
          <button type="submit">Create</button>
        </form>
      </section>

      <section className="panel">
        <div className="row row-wrap">
          <h3>Room List</h3>
          <label>
            Filter
            <select value={channelFilter} onChange={(event) => setChannelFilter(event.target.value)}>
              <option value="">All channels</option>
              {CHANNEL_OPTIONS.map((channel) => (
                <option key={channel} value={channel}>
                  {channelLabel(channel)}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={fetchChatrooms}>
            Apply
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Channel</th>
                <th>External Room ID</th>
                <th>Threads</th>
                <th>AI</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {chatrooms.length === 0 && (
                <tr>
                  <td colSpan="7">No chatrooms found.</td>
                </tr>
              )}
              {chatrooms.map((room) => (
                <tr key={room.id}>
                  <td>{room.name}</td>
                  <td>{channelLabel(room.channel)}</td>
                  <td>{room.external_room_id}</td>
                  <td>{room.thread_count}</td>
                  <td>{room.ai_enabled ? "Enabled" : "Paused"}</td>
                  <td>{formatDateTime(room.updated_at)}</td>
                  <td className="actions-cell">
                    <Link to={`/inbox/${room.id}`}>Open Inbox</Link>
                    <Link to={`/ai-settings?chatroomId=${room.id}`}>AI Settings</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
