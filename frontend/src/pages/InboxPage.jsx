/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { channelLabel, formatDateTime } from "../lib/format";

const outboundDefaults = {
  content: "",
  sender_type: "agent",
};

export default function InboxPage() {
  const navigate = useNavigate();
  const { chatroomId } = useParams();
  const routeChatroomId = Number(chatroomId) || null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [outbound, setOutbound] = useState(outboundDefaults);

  const selectedChatroom = useMemo(
    () => chatrooms.find((room) => room.id === routeChatroomId) || null,
    [chatrooms, routeChatroomId],
  );
  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) || null,
    [threads, selectedThreadId],
  );

  const fetchChatrooms = useCallback(async () => {
    setError("");
    try {
      const rows = await api.listChatrooms();
      setChatrooms(rows);
      return rows;
    } catch (fetchError) {
      setError(fetchError.message);
      return [];
    }
  }, []);

  const fetchThreads = useCallback(async (roomId, preferredThreadId = null) => {
    if (!roomId) {
      setThreads([]);
      setSelectedThreadId(null);
      setMessages([]);
      return;
    }
    setError("");
    try {
      const rows = await api.listThreads(roomId);
      setThreads(rows);
      const nextThreadId =
        (preferredThreadId && rows.find((item) => item.id === preferredThreadId)?.id) ||
        rows[0]?.id ||
        null;
      setSelectedThreadId(nextThreadId);
      return nextThreadId;
    } catch (fetchError) {
      setError(fetchError.message);
      return null;
    }
  }, []);

  const fetchMessages = useCallback(async (threadId) => {
    if (!threadId) {
      setMessages([]);
      return;
    }
    setError("");
    try {
      const rows = await api.listMessages(threadId);
      setMessages(rows);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }, []);

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      const rooms = await fetchChatrooms();
      if (rooms.length > 0 && !routeChatroomId) {
        navigate(`/inbox/${rooms[0].id}`, { replace: true });
      }
      setLoading(false);
    }
    bootstrap();
  }, [fetchChatrooms, navigate, routeChatroomId]);

  useEffect(() => {
    fetchThreads(routeChatroomId);
  }, [fetchThreads, routeChatroomId]);

  useEffect(() => {
    fetchMessages(selectedThreadId);
  }, [fetchMessages, selectedThreadId]);

  function handleSelectChatroom(nextRoomId) {
    navigate(`/inbox/${nextRoomId}`);
  }

  async function handleSendMessage(event) {
    event.preventDefault();
    if (!selectedThreadId || !outbound.content.trim()) return;
    setError("");
    setNotice("");
    try {
      await api.sendMessage(selectedThreadId, outbound);
      await fetchMessages(selectedThreadId);
      if (routeChatroomId) {
        await fetchThreads(routeChatroomId, selectedThreadId);
      }
      setOutbound((previous) => ({ ...previous, content: "" }));
      setNotice("Message sent.");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <section className="page">
      <header className="page-header-row">
        <div>
          <h2>Inbox</h2>
          <p className="muted">Thread-based conversations by selected chatroom.</p>
        </div>
        <button type="button" onClick={() => fetchThreads(routeChatroomId, selectedThreadId)}>
          Refresh
        </button>
      </header>

      {loading && <p className="notice">Loading...</p>}
      {notice && <p className="notice success">{notice}</p>}
      {error && <p className="notice error">{error}</p>}

      <section className="panel">
        <label>
          Chatroom
          <select
            value={routeChatroomId || ""}
            onChange={(event) => handleSelectChatroom(event.target.value)}
          >
            {chatrooms.length === 0 && <option value="">No chatrooms available</option>}
            {chatrooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.name} ({channelLabel(room.channel)})
              </option>
            ))}
          </select>
        </label>
        {selectedChatroom && (
          <p className="muted">
            {selectedChatroom.external_room_id} · AI {selectedChatroom.ai_enabled ? "enabled" : "paused"}
          </p>
        )}
      </section>

      <section className="inbox-grid">
        <div className="panel">
          <h3>Threads</h3>
          <ul className="list">
            {threads.length === 0 && <li className="list-item">No threads yet.</li>}
            {threads.map((thread) => (
              <li
                key={thread.id}
                className={`list-item clickable ${thread.id === selectedThreadId ? "active-item" : ""}`}
                onClick={() => setSelectedThreadId(thread.id)}
              >
                <p className="item-title">{thread.contact_display_name || thread.contact_external_user_id}</p>
                <p className="item-sub">
                  {channelLabel(thread.contact_channel)} · {thread.status}
                </p>
                <p className="item-sub">{thread.last_message_preview || "-"}</p>
                <p className="item-sub">{formatDateTime(thread.last_message_at)}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h3>Messages</h3>
          {!selectedThread && <p className="muted">Select a thread to start.</p>}
          {selectedThread && (
            <>
              <p className="muted">
                Thread #{selectedThread.id} · {selectedThread.contact_display_name || selectedThread.contact_external_user_id}
              </p>
              <div className="message-box">
                {messages.length === 0 && <p className="item-sub">No messages yet.</p>}
                {messages.map((msg) => (
                  <div key={msg.id} className={`message-row ${msg.direction === "outbound" ? "outbound" : "inbound"}`}>
                    <p className="message-meta">
                      {msg.sender_type} · {formatDateTime(msg.created_at)}
                    </p>
                    <p className="message-content">{msg.content}</p>
                  </div>
                ))}
              </div>
              <form onSubmit={handleSendMessage} className="row row-wrap">
                <select
                  value={outbound.sender_type}
                  onChange={(event) => setOutbound((previous) => ({ ...previous, sender_type: event.target.value }))}
                >
                  <option value="agent">agent</option>
                  <option value="system">system</option>
                </select>
                <input
                  className="compose-input"
                  value={outbound.content}
                  onChange={(event) => setOutbound((previous) => ({ ...previous, content: event.target.value }))}
                  placeholder="Type outbound message"
                  required
                />
                <button type="submit">Send</button>
              </form>
            </>
          )}
        </div>
      </section>
    </section>
  );
}
