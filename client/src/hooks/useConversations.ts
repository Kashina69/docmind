"use client";

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Conversation } from "@/lib/types";
import { supabaseFetch } from "@/lib/supabase";

interface UseConversationsReturn {
	conversations: Conversation[];
	loading: boolean;
	error: string | null;
	createConversation: (
		title?: string,
		documentIds?: string[],
	) => Promise<Conversation | null>;
	deleteConversation: (id: string) => Promise<boolean>;
	refresh: () => void;
}

export function useConversations(): UseConversationsReturn {
	const [conversations, setConversations] = useState<Conversation[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchConversations = useCallback(async () => {
		try {
			const data = await supabaseFetch<Conversation[]>(
				"conversations?select=*,conversation_documents(document_id)&order=updated_at.desc",
			);
			const mapped = data.map((conv: Conversation & {
				conversation_documents?: { document_id: string }[];
			}) => ({
				...conv,
				documentIds: (conv.conversation_documents ?? []).map(
					(cd) => cd.document_id,
				),
			}));
			setConversations(mapped);
			setError(null);
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "Failed to load conversations",
			);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchConversations();
	}, [fetchConversations]);

	const createConversation = useCallback(
		async (
			title = "New Conversation",
			documentIds?: string[],
		): Promise<Conversation | null> => {
			try {
				const supabase = createClient();
				const {
					data: { session },
				} = await supabase.auth.getSession();
				if (!session) return null;

				const newConv = {
					id: crypto.randomUUID(),
					user_id: session.user.id,
					title,
					...(documentIds?.length
						? { document_id: documentIds[0] }
						: {}),
				};

				const result = await supabaseFetch<Conversation[]>(
					"conversations",
					{
						method: "POST",
						headers: { Prefer: "return=representation" },
						body: JSON.stringify(newConv),
					},
				);

				const created = Array.isArray(result) ? result[0] : result;

				if (documentIds && documentIds.length > 0) {
					await supabase
						.schema("rag")
						.from("conversation_documents")
						.insert(
							documentIds.map((docId) => ({
								conversation_id: created.id,
								document_id: docId,
							})),
						);
				}

				const withIds: Conversation = {
					...created,
					documentIds: documentIds ?? [],
				};
				setConversations((prev) => [withIds, ...prev]);
				return withIds;
			} catch (err) {
				console.error("Failed to create conversation:", err);
				return null;
			}
		},
		[],
	);

	const deleteConversation = useCallback(
		async (id: string): Promise<boolean> => {
			const previous = conversations;
			setConversations((prev) => prev.filter((c) => c.id !== id));
			try {
				const { deleteConversationApi } = await import(
					"@/services/conversations"
				);
				await deleteConversationApi(id);
				return true;
			} catch (err) {
				console.error("Failed to delete conversation:", err);
				setConversations(previous);
				return false;
			}
		},
		[conversations],
	);

	return {
		conversations,
		loading,
		error,
		createConversation,
		deleteConversation,
		refresh: fetchConversations,
	};
}
