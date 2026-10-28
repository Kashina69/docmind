import type { PollResult, QueryRequest, QueryResponse } from "@/lib/types";
import { backendFetch } from "./api";

export function submitQuery(req: QueryRequest): Promise<QueryResponse> {
	return backendFetch<QueryResponse>("/query", {
		method: "POST",
		body: JSON.stringify(req),
	});
}

export function fetchQueryResult(jobId: string): Promise<PollResult> {
	return backendFetch<PollResult>(`/result/${jobId}`);
}
