import { useParams } from "next/navigation";

export function useSessionId(): string {
  return useParams<{ id: string }>().id;
}
