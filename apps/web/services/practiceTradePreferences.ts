"use client";

import { useCallback, useSyncExternalStore } from "react";

const VOLUME_STORAGE_KEY = "forex-intelligence:practice-volume";
const VOLUME_CHANGE_EVENT = "forex-intelligence:practice-volume-change";
const DEFAULT_VOLUME = "0.01";
let currentVolume: string | null = null;

function isValidVolume(value: unknown): value is string {
  if (typeof value !== "string" || !value.trim()) return false;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0;
}

function getVolumeSnapshot(): string {
  if (currentVolume !== null) return currentVolume;
  try {
    const saved = window.localStorage.getItem(VOLUME_STORAGE_KEY);
    return isValidVolume(saved) ? saved : DEFAULT_VOLUME;
  } catch {
    return DEFAULT_VOLUME;
  }
}

function subscribeToVolumeChanges(notify: () => void): () => void {
  function onStorageChange() {
    currentVolume = null;
    notify();
  }
  window.addEventListener("storage", onStorageChange);
  window.addEventListener(VOLUME_CHANGE_EVENT, notify);
  return () => {
    window.removeEventListener("storage", onStorageChange);
    window.removeEventListener(VOLUME_CHANGE_EVENT, notify);
  };
}

export function usePracticeVolume() {
  const volume = useSyncExternalStore(subscribeToVolumeChanges, getVolumeSnapshot, () => DEFAULT_VOLUME);
  const setVolume = useCallback((nextVolume: string) => {
    currentVolume = nextVolume;
    if (isValidVolume(nextVolume)) {
      try {
        window.localStorage.setItem(VOLUME_STORAGE_KEY, nextVolume);
      } catch {
        // Keep the in-memory volume when browser storage is unavailable.
      }
    }
    window.dispatchEvent(new Event(VOLUME_CHANGE_EVENT));
  }, []);

  return { volume, setVolume };
}
