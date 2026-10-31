"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { getAccessCode, setAccessCode, UNAUTHORIZED_EVENT } from "@/lib/api";

import { Button } from "./ui/primitives";

/** Opens on any 401 from the API; the code lives in sessionStorage and is sent by lib/api on every call. */
export function AccessCodePrompt() {
  const queryClient = useQueryClient();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [code, setCode] = useState("");
  const [wasRejected, setWasRejected] = useState(false);

  useEffect(() => {
    const open = () => {
      setWasRejected(getAccessCode() !== "");
      if (!dialogRef.current?.open) dialogRef.current?.showModal();
    };
    window.addEventListener(UNAUTHORIZED_EVENT, open);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, open);
  }, []);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;
    setAccessCode(trimmed);
    setCode("");
    dialogRef.current?.close();
    queryClient.invalidateQueries();
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="access-code-title"
      className="m-auto w-[min(92vw,420px)] rounded-lg border border-line-strong bg-surface p-0 text-ink backdrop:bg-canvas/80"
    >
      <form onSubmit={handleSubmit} className="space-y-3 p-5">
        <h2 id="access-code-title" className="text-lg font-semibold">
          Access code
        </h2>
        <p className="text-sm text-ink-muted">This hosted demo is gated. Enter the access code you were given.</p>
        {wasRejected && (
          <p role="alert" className="text-sm text-st-mismatched">
            The stored code was not accepted. Enter it again.
          </p>
        )}
        <div>
          <label htmlFor="access-code" className="text-sm font-medium">
            Code
          </label>
          <input
            id="access-code"
            type="password"
            autoComplete="off"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-1 block min-h-10 w-full rounded-md border border-line-strong bg-surface-2 px-3 text-sm focus:border-accent focus:outline-none"
          />
        </div>
        <Button type="submit" variant="primary" disabled={!code.trim()}>
          Continue
        </Button>
      </form>
    </dialog>
  );
}
