// Lightweight, dependency-free event-bus toast system.
// Usage: import { toast } from '@/lib/toast'; toast('Done!');

export type ToastVariant = 'success' | 'error' | 'info';

export interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

type Listener = (toasts: ToastItem[]) => void;

let _toasts: ToastItem[] = [];
let _listeners: Listener[] = [];
let _nextId = 0;

function notify() {
  _listeners.forEach((l) => l([..._toasts]));
}

export function toast(message: string, variant: ToastVariant = 'success', durationMs = 2500) {
  const id = _nextId++;
  _toasts = [..._toasts, { id, message, variant }];
  notify();
  setTimeout(() => {
    _toasts = _toasts.filter((t) => t.id !== id);
    notify();
  }, durationMs);
}

export function subscribeToasts(listener: Listener) {
  _listeners.push(listener);
  listener([..._toasts]); // immediate sync
  return () => {
    _listeners = _listeners.filter((l) => l !== listener);
  };
}
