"use client";

import { useEffect, useState } from "react";

import { getToken, setToken } from "./api";

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTokenState(getToken());
    setReady(true);
  }, []);

  const login = (t: string) => {
    setToken(t);
    setTokenState(t);
  };

  const logout = () => {
    setToken(null);
    setTokenState(null);
  };

  return { token, ready, isAuthenticated: !!token, login, logout };
}
