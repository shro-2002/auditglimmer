"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button, Card, ErrorState } from "@/components/ui/primitives";
import { api, queryKeys } from "@/lib/api";

const NAME_MAX = 120;
const FACILITY_MAX = 40;
const FACILITY_PATTERN = /^[A-Za-z0-9_-]{1,40}$/;

const INPUT =
  "mt-1 block min-h-10 w-full rounded-md border border-line-strong bg-surface-2 px-3 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none";

export default function NewSessionPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [facility, setFacility] = useState("");
  const [touched, setTouched] = useState(false);

  const create = useMutation({
    mutationFn: api.createSession,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.overview });
      router.push(`/sessions/${session.id}`);
    },
  });

  const nameError = name.trim().length === 0 ? "Name is required." : null;
  const facilityError = FACILITY_PATTERN.test(facility)
    ? null
    : "1–40 characters: letters, digits, underscore or hyphen.";

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setTouched(true);
    if (nameError || facilityError) return;
    create.mutate({ name: name.trim(), facility_id: facility });
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">New audit session</h1>
      <Card>
        <form data-testid="create-session-form" noValidate onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="session-name" className="text-sm font-medium">
              Session name
            </label>
            <input
              id="session-name"
              name="name"
              className={INPUT}
              value={name}
              maxLength={NAME_MAX}
              required
              aria-invalid={touched && !!nameError}
              aria-describedby={touched && nameError ? "session-name-error" : undefined}
              onChange={(e) => setName(e.target.value)}
              placeholder="Q4 collateral inspection — Warehouse 7"
            />
            {touched && nameError && (
              <p id="session-name-error" className="mt-1 text-xs text-st-mismatched">
                {nameError}
              </p>
            )}
          </div>
          <div>
            <label htmlFor="facility-id" className="text-sm font-medium">
              Facility ID
            </label>
            <input
              id="facility-id"
              name="facility_id"
              className={`${INPUT} font-mono`}
              value={facility}
              maxLength={FACILITY_MAX}
              required
              aria-invalid={touched && !!facilityError}
              aria-describedby="facility-help"
              onChange={(e) => setFacility(e.target.value)}
              placeholder="WH-07"
            />
            <p id="facility-help" className={`mt-1 text-xs ${touched && facilityError ? "text-st-mismatched" : "text-ink-muted"}`}>
              {touched && facilityError ? facilityError : "Must match the facility_id used in the ledger CSV."}
            </p>
          </div>
          {create.isError && <ErrorState title="Session was not created" error={create.error} />}
          <Button type="submit" variant="primary" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create session"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
