import { supabaseFetch } from "@/lib/supabase";
import type { Message } from "@/lib/types";

export async function listMessages(
	conversationId: string,
): Promise<Message[]> {
	const raw = await supabaseFetch<Message[]>(
		`messages?conversation_id=eq.${conversationId}&order=created_at.asc`,
	);

	return raw.map((msg) => {
		if (
			msg.role !== "assistant" ||
			msg.sources?.length ||
			!msg.retrieved_chunks?.length
		) {
			return msg;
		}
		return {
			...msg,
			sources: msg.retrieved_chunks.map((c) => ({
				chunk_id: c.id ?? null,
				document_id: c.document_id ?? null,
				page_number: c.page_number ?? null,
				filename: c.filename ?? "",
				section: c.section ?? null,
				snippet: c.content ?? "",
			})),
		};
	});
}
