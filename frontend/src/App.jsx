import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ChatroomsPage from "./pages/ChatroomsPage";
import InboxPage from "./pages/InboxPage";
import AISettingsPage from "./pages/AISettingsPage";
import SimulatorPage from "./pages/SimulatorPage";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/chatrooms" replace />} />
          <Route path="/chatrooms" element={<ChatroomsPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/inbox/:chatroomId" element={<InboxPage />} />
          <Route path="/ai-settings" element={<AISettingsPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="*" element={<Navigate to="/chatrooms" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
