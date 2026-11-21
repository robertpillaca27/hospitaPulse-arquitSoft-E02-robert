"use client";

import { useEffect } from "react";

const SESSION_EXPIRES_AT_KEY = "hospitapulse_session_expires_at";
const SESSION_STARTED_EVENT = "hospitapulse-session-started";
const SESSION_ENDED_EVENT = "hospitapulse-session-ended";

export default function SessionExpiration() {
  useEffect(() => {
    let timeout: number | undefined;
    const clearTimeoutIfSet = () => {
      if (timeout !== undefined) window.clearTimeout(timeout);
      timeout = undefined;
    };
    const expireSession = () => {
      clearTimeoutIfSet();
      window.sessionStorage.removeItem(SESSION_EXPIRES_AT_KEY);
      window.location.replace("/");
    };
    const armTimeout = () => {
      clearTimeoutIfSet();
      const expiresAt = Number(window.sessionStorage.getItem(SESSION_EXPIRES_AT_KEY));
      if (!Number.isFinite(expiresAt) || expiresAt <= 0) return;
      const remaining = expiresAt - Date.now();
      if (remaining <= 0) {
        expireSession();
        return;
      }
      timeout = window.setTimeout(expireSession, remaining);
    };
    const clearSessionTimeout = () => clearTimeoutIfSet();

    armTimeout();
    window.addEventListener(SESSION_STARTED_EVENT, armTimeout);
    window.addEventListener(SESSION_ENDED_EVENT, clearSessionTimeout);
    window.addEventListener("focus", armTimeout);
    return () => {
      clearTimeoutIfSet();
      window.removeEventListener(SESSION_STARTED_EVENT, armTimeout);
      window.removeEventListener(SESSION_ENDED_EVENT, clearSessionTimeout);
      window.removeEventListener("focus", armTimeout);
    };
  }, []);

  return null;
}
