import { useCallback, useEffect, useMemo, useState } from "react";
import { api, apiBaseUrl } from "./api";
import "./App.css";

const channelOptions = ["whatsapp", "wechat", "facebook", "instagram"];

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function App() {
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [chatroomFilter, setChatroomFilter] = useState("");
  const [chatrooms, setChatrooms] = useState([]);
  const [selectedChatroomId, setSelectedChatroomId] = useState(null);

  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [messages, setMessages] = useState([]);

  const [chatroomForm, setChatroomForm] = useState({
    name: "",
    channel: "whatsapp",
    external_room_id: "",
  });
  const [scheduleForm, setScheduleForm] = useState({
    ai_schedule_start: "00:00",
    ai_schedule_end: "00:00",
    timezone: "Asia/Hong_Kong",
  });
  const [simulateForm, setSimulateForm] = useState({
    channel: "whatsapp",
    chatroom_external_id: "house88-whatsapp",
    contact_id: "",
    contact_name: "",
    text: "",
  });
  const [outboundForm, setOutboundForm] = useState({
    content: "",
    sender_type: "agent",
  });

  const selectedChatroom = useMemo(
    () => chatrooms.find((room) => room.id === selectedChatroomId) || null,
    [chatrooms, selectedChatroomId],
  );
  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) || null,
    [threads, selectedThreadId],
  );

  const refreshMessages = useCallback(async (threadId) => {
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

  const refreshThreads = useCallback(
    async (chatroomId, threadIdHint = null) => {
      if (!chatroomId) {
        setThreads([]);
        setSelectedThreadId(null);
        setMessages([]);
        return null;
      }
      setError("");
      try {
        const rows = await api.listThreads(chatroomId);
        setThreads(rows);
        const nextThreadId =
          (threadIdHint && rows.find((item) => item.id === threadIdHint)?.id) ||
          (selectedThreadId && rows.find((item) => item.id === selectedThreadId)?.id) ||
          rows[0]?.id ||
          null;
        setSelectedThreadId(nextThreadId);
        await refreshMessages(nextThreadId);
        return nextThreadId;
      } catch (fetchError) {
        setError(fetchError.message);
        return null;
      }
    },
    [refreshMessages, selectedThreadId],
  );

  const refreshChatrooms = useCallback(
    async (roomIdHint = null, threadIdHint = null) => {
      setError("");
      try {
        const rows = await api.listChatrooms(chatroomFilter ? { channel: chatroomFilter } : undefined);
        setChatrooms(rows);
        const nextRoomId =
          (roomIdHint && rows.find((item) => item.id === roomIdHint)?.id) ||
          rows[0]?.id ||
          null;

        setSelectedChatroomId(nextRoomId);
        const room = rows.find((item) => item.id === nextRoomId) || null;
        if (room) {
          setScheduleForm({
            ai_schedule_start: room.ai_schedule_start,
            ai_schedule_end: room.ai_schedule_end,
            timezone: room.timezone,
          });
          setSimulateForm((previous) => ({
            ...previous,
            channel: room.channel,
            chatroom_external_id: room.external_room_id,
          }));
          await refreshThreads(room.id, threadIdHint);
        } else {
          setThreads([]);
          setSelectedThreadId(null);
          setMessages([]);
        }
      } catch (fetchError) {
        setError(fetchError.message);
      }
    },
    [chatroomFilter, refreshThreads],
  );

  const selectChatroom = useCallback(
    async (room) => {
      setSelectedChatroomId(room.id);
      setScheduleForm({
        ai_schedule_start: room.ai_schedule_start,
        ai_schedule_end: room.ai_schedule_end,
        timezone: room.timezone,
      });
      setSimulateForm((previous) => ({
        ...previous,
        channel: room.channel,
        chatroom_external_id: room.external_room_id,
      }));
      await refreshThreads(room.id);
    },
    [refreshThreads],
  );

  const selectThread = useCallback(
    async (threadId) => {
      setSelectedThreadId(threadId);
      await refreshMessages(threadId);
    },
    [refreshMessages],
  );

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      await refreshChatrooms();
      setLoading(false);
    }
    bootstrap();
  }, [refreshChatrooms]);

  async function handleCreateChatroom(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const created = await api.createChatroom({
        name: chatroomForm.name,
        channel: chatroomForm.channel,
        external_room_id: chatroomForm.external_room_id,
        ai_enabled: true,
        ai_schedule_start: "00:00",
        ai_schedule_end: "00:00",
        timezone: "Asia/Hong_Kong",
      });
      setChatroomForm((previous) => ({ ...previous, name: "", external_room_id: "" }));
      await refreshChatrooms(created.id);
      setNotice("已新增 chatroom。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleToggleChatroomAI() {
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.updateChatroomAIStatus(selectedChatroom.id, !selectedChatroom.ai_enabled);
      await refreshChatrooms(selectedChatroom.id);
      setNotice(`已${selectedChatroom.ai_enabled ? "停用" : "啟用"}此 chatroom 的 AI。`);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handlePauseChatroomAI() {
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.pauseChatroomAI(selectedChatroom.id);
      await refreshChatrooms(selectedChatroom.id);
      setNotice("已一鍵停用此 chatroom AI。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleUpdateSchedule(event) {
    event.preventDefault();
    if (!selectedChatroom) return;
    setError("");
    setNotice("");
    try {
      await api.updateChatroomSchedule(
        selectedChatroom.id,
        scheduleForm.ai_schedule_start,
        scheduleForm.ai_schedule_end,
        scheduleForm.timezone,
      );
      await refreshChatrooms(selectedChatroom.id);
      setNotice("AI 時段已更新。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleSimulateInbound(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const result = await api.simulateIncoming(simulateForm);
      await refreshChatrooms(result.chatroom_id, result.thread_id);
      setNotice(`模擬 inbound 成功（${result.channel} / AI reply: ${result.ai_replied ? "yes" : "no"}）。`);
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  async function handleSendMessage(event) {
    event.preventDefault();
    if (!selectedThreadId || !outboundForm.content.trim()) return;
    setError("");
    setNotice("");
    try {
      await api.sendMessage(selectedThreadId, outboundForm);
      if (selectedChatroomId) {
        await refreshThreads(selectedChatroomId, selectedThreadId);
      }
      setOutboundForm((previous) => ({ ...previous, content: "" }));
      setNotice("訊息已發送。");
    } catch (fetchError) {
      setError(fetchError.message);
    }
  }

  return (
    <main className="layout">
      <header className="page-header">
        <div>
          <h1>House 88 Omnichannel Chatroom</h1>
          <p className="subtext">WhatsApp / WeChat / Facebook / Instagram unified inbox · API: {apiBaseUrl}</p>
        </div>
        <button type="button" onClick={() => refreshChatrooms(selectedChatroomId)}>
          Refresh
        </button>
      </header>

      {loading && <p className="notice">載入中...</p>}
      {notice && <p className="notice success">{notice}</p>}
      {error && <p className="notice error">{error}</p>}

      <section className="panel top-grid">
        <div>
          <h2>Create Chatroom</h2>
          <form onSubmit={handleCreateChatroom} className="row row-wrap form-grid">
            <label>
              Name
              <input
                value={chatroomForm.name}
                onChange={(event) => setChatroomForm((previous) => ({ ...previous, name: event.target.value }))}
                required
              />
            </label>
            <label>
              Channel
              <select
                value={chatroomForm.channel}
                onChange={(event) => setChatroomForm((previous) => ({ ...previous, channel: event.target.value }))}
              >
                {channelOptions.map((channel) => (
                  <option key={channel} value={channel}>
                    {channel}
                  </option>
                ))}
              </select>
            </label>
            <label>
              External Room ID
              <input
                value={chatroomForm.external_room_id}
                onChange={(event) =>
                  setChatroomForm((previous) => ({ ...previous, external_room_id: event.target.value }))
                }
                required
              />
            </label>
            <button type="submit">Create</button>
          </form>
        </div>

        <div>
          <h2>Simulate Inbound</h2>
          <form onSubmit={handleSimulateInbound} className="row row-wrap form-grid">
            <label>
              Channel
              <select
                value={simulateForm.channel}
                onChange={(event) => setSimulateForm((previous) => ({ ...previous, channel: event.target.value }))}
              >
                {channelOptions.map((channel) => (
                  <option key={channel} value={channel}>
                    {channel}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Chatroom External ID
              <input
                value={simulateForm.chatroom_external_id}
                onChange={(event) =>
                  setSimulateForm((previous) => ({ ...previous, chatroom_external_id: event.target.value }))
                }
                required
              />
            </label>
            <label>
              Contact ID
              <input
                value={simulateForm.contact_id}
                onChange={(event) => setSimulateForm((previous) => ({ ...previous, contact_id: event.target.value }))}
                required
              />
            </label>
            <label>
              Contact Name
              <input
                value={simulateForm.contact_name}
                onChange={(event) =>
                  setSimulateForm((previous) => ({ ...previous, contact_name: event.target.value }))
                }
              />
            </label>
            <label className="wide-field">
              Message
              <input
                value={simulateForm.text}
                onChange={(event) => setSimulateForm((previous) => ({ ...previous, text: event.target.value }))}
                required
              />
            </label>
            <button type="submit">Send Inbound</button>
          </form>
        </div>
      </section>

      <section className="inbox-grid">
        <div className="panel">
          <div className="row row-wrap">
            <h2>Chatrooms</h2>
            <label>
              Channel Filter
              <select
                value={chatroomFilter}
                onChange={(event) => setChatroomFilter(event.target.value)}
              >
                <option value="">all</option>
                {channelOptions.map((channel) => (
                  <option key={channel} value={channel}>
                    {channel}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={() => refreshChatrooms(selectedChatroomId)}>
              Apply
            </button>
          </div>
          <ul className="list">
            {chatrooms.length === 0 && <li className="list-item">No chatrooms.</li>}
            {chatrooms.map((room) => (
              <li
                key={room.id}
                className={`list-item clickable ${room.id === selectedChatroomId ? "active-item" : ""}`}
                onClick={() => {
                  selectChatroom(room);
                }}
              >
                <p className="item-title">{room.name}</p>
                <p className="item-sub">
                  {room.channel} · {room.external_room_id}
                </p>
                <p className="item-sub">
                  AI: {room.ai_enabled ? "on" : "off"} · Threads: {room.thread_count}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h2>Threads {selectedChatroom ? `· ${selectedChatroom.name}` : ""}</h2>
          {!selectedChatroom && <p>Select a chatroom first.</p>}
          {selectedChatroom && (
            <>
              <div className="ai-toolbar">
                <p>
                  <strong>AI:</strong> {selectedChatroom.ai_enabled ? "Enabled" : "Paused"}
                </p>
                <p>
                  <strong>Schedule:</strong> {selectedChatroom.ai_schedule_start} - {selectedChatroom.ai_schedule_end} (
                  {selectedChatroom.timezone})
                </p>
                <button type="button" onClick={handleToggleChatroomAI}>
                  {selectedChatroom.ai_enabled ? "Disable AI" : "Enable AI"}
                </button>
                <button type="button" onClick={handlePauseChatroomAI}>
                  One-click Pause
                </button>
              </div>
              <form onSubmit={handleUpdateSchedule} className="row row-wrap compact-form">
                <label>
                  Start
                  <input
                    type="time"
                    value={scheduleForm.ai_schedule_start}
                    onChange={(event) =>
                      setScheduleForm((previous) => ({ ...previous, ai_schedule_start: event.target.value }))
                    }
                    required
                  />
                </label>
                <label>
                  End
                  <input
                    type="time"
                    value={scheduleForm.ai_schedule_end}
                    onChange={(event) =>
                      setScheduleForm((previous) => ({ ...previous, ai_schedule_end: event.target.value }))
                    }
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
                <button type="submit">Update</button>
              </form>
              <ul className="list">
                {threads.length === 0 && <li className="list-item">No threads yet.</li>}
                {threads.map((thread) => (
                  <li
                    key={thread.id}
                    className={`list-item clickable ${thread.id === selectedThreadId ? "active-item" : ""}`}
                    onClick={() => {
                      selectThread(thread.id);
                    }}
                  >
                    <p className="item-title">{thread.contact_display_name || thread.contact_external_user_id}</p>
                    <p className="item-sub">
                      {thread.contact_channel} · {thread.status}
                    </p>
                    <p className="item-sub">{thread.last_message_preview || "-"}</p>
                    <p className="item-sub">{formatDateTime(thread.last_message_at)}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="panel">
          <h2>Messages</h2>
          {!selectedThread && <p>Select a thread to view messages.</p>}
          {selectedThread && (
            <>
              <p className="item-sub">
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
                  value={outboundForm.sender_type}
                  onChange={(event) => setOutboundForm((previous) => ({ ...previous, sender_type: event.target.value }))}
                >
                  <option value="agent">agent</option>
                  <option value="system">system</option>
                </select>
                <input
                  className="compose-input"
                  placeholder="Type outbound message"
                  value={outboundForm.content}
                  onChange={(event) => setOutboundForm((previous) => ({ ...previous, content: event.target.value }))}
                  required
                />
                <button type="submit">Send</button>
              </form>
            </>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
