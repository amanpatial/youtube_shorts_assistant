import { useEffect, useState } from "react";
import "./App.css";
import Create from "./pages/Create";
import Detail from "./pages/Detail";
import History from "./pages/History";
import Settings from "./pages/Settings";

function parseHash(hash: string): { page: string; id?: string } {
  const raw = (hash || "#/").replace(/^#/, "") || "/";
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  if (path === "/" || path === "/create") {
    return { page: "create" };
  }
  if (path === "/history") {
    return { page: "history" };
  }
  if (path === "/settings") {
    return { page: "settings" };
  }
  const run = path.match(/^\/runs\/([^/]+)$/);
  if (run) {
    return { page: "detail", id: run[1] };
  }
  return { page: "create" };
}

export default function App() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));

  useEffect(() => {
    const onHash = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="shell">
      <header className="top">
        <h1>Shorts Assistant</h1>
        <nav className="nav">
          <a className={route.page === "create" ? "active" : ""} href="#/">
            Create
          </a>
          <a className={route.page === "history" ? "active" : ""} href="#/history">
            History
          </a>
          <a className={route.page === "settings" ? "active" : ""} href="#/settings">
            Settings
          </a>
        </nav>
      </header>
      {route.page === "create" ? <Create /> : null}
      {route.page === "history" ? <History /> : null}
      {route.page === "settings" ? <Settings /> : null}
      {route.page === "detail" && route.id ? <Detail workflowId={route.id} /> : null}
    </div>
  );
}
