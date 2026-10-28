import type { Conversation } from "@/lib/types";
import { backendFetch } from "./api";

export function deleteConversationApi(
	id: string,
): Promise<{ deleted: boolean }> {
	return backendFetch<{ deleted: boolean }>(`/conversations/${id}`, {
		method: "DELETE",
	});
}

export function listConversations(): Promise<Conversation[]> {
	return backendFetch<Conversation[]>("/conversations");
}
