"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "forex-intelligence:selected-instrument";

export function useInstrumentSelection(defaultSymbol = "EURUSD") {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [ready, setReady] = useState(false);
  const [hasSavedSelection, setHasSavedSelection] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = window.localStorage.getItem(STORAGE_KEY);
        if (saved) {
          setSymbol(saved);
          setHasSavedSelection(true);
        }
      } catch {
        setHasSavedSelection(false);
      }
      setReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const selectSymbol = useCallback((nextSymbol: string) => {
    setSymbol(nextSymbol);
    setHasSavedSelection(true);
    try {
      window.localStorage.setItem(STORAGE_KEY, nextSymbol);
    } catch {
      // Keep the in-memory selection if browser storage is unavailable.
    }
  }, []);

  return { symbol, setSymbol: selectSymbol, ready, hasSavedSelection };
}
