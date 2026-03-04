import { NavLink, Outlet } from "react-router-dom";
import { apiBaseUrl } from "../api";

function navClass({ isActive }) {
  return `nav-link${isActive ? " active-link" : ""}`;
}

export default function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1 className="brand">House 88 Omnichat</h1>
        <p className="sidebar-subtext">Unified inbox for 4 channels</p>
        <nav className="nav">
          <NavLink to="/chatrooms" className={navClass}>
            Chatrooms
          </NavLink>
          <NavLink to="/inbox" className={navClass}>
            Inbox
          </NavLink>
          <NavLink to="/ai-settings" className={navClass}>
            AI Settings
          </NavLink>
          <NavLink to="/simulator" className={navClass}>
            Simulator
          </NavLink>
        </nav>
        <p className="sidebar-api">API: {apiBaseUrl}</p>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
