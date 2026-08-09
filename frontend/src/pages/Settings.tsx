import { FormEvent, useState } from "react";
import { getApiKey, setApiKey } from "../api";

export default function Settings() {
  const [key, setKey] = useState(getApiKey());
  const [saved, setSaved] = useState(false);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setApiKey(key);
    setSaved(true);
  }

  return (
    <div className="card">
      <h2>Settings</h2>
      <p className="muted">
        Same value as server <code>API_KEY</code> (for example <code>dev-change-me</code>).
        Stored only in this browser.
      </p>
      <form onSubmit={onSubmit}>
        <label htmlFor="api-key">API key</label>
        <input
          id="api-key"
          type="password"
          autoComplete="off"
          value={key}
          onChange={(e) => {
            setKey(e.target.value);
            setSaved(false);
          }}
        />
        <div className="actions">
          <button className="btn" type="submit">
            Save
          </button>
        </div>
      </form>
      {saved ? <p className="muted">Saved.</p> : null}
    </div>
  );
}
