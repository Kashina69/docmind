"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PaperPlaneRight } from "@/components/icons";
import { Button, Input, toast } from "@/components/ui";
import { useConversations } from "@/hooks/useConversations";
import { useMessages } from "@/hooks/useMessages";
import { useRAGQuery } from "@/hooks/useRAGQuery";
import type { Conversation, Message, ResponseStyle } from "@/lib/types";
import { ChatSidebar } from "../components/ChatSidebar";

const STYLES: { value: ResponseStyle; label: string }[] = [
	{ value: "explanatory", label: "Detailed" },
	{ value: "concise", label: "Concise" },
	{ value: "conversational", label: "Casual" },
];

export default function ChatPage() {
	const {
		conversations,
		createConversation,
		refresh: refreshConversations,
	} = useConversations();
	const [activeChatId, setActiveChatId] = useState<string | null>(null);
	const { messages, addMessage, refresh: refreshMessages } =
		useMessages(activeChatId);
	const { submit, isLoading } = useRAGQuery();

	const [input, setInput] = useState("");
	const [style, setStyle] = useState<ResponseStyle>("explanatory");

	useEffect(() => {
		if (!activeChatId && conversations.length > 0) {
			setActiveChatId(conversations[0].id);
		}
	}, [conversations, activeChatId]);

	const activeConversation = useMemo(
		() => conversations.find((c) => c.id === activeChatId) ?? null,
		[conversations, activeChatId],
	);

	const handleSelectChat = useCallback((id: string) => {
		setActiveChatId(id);
	}, []);

	const handleChatsChange = useCallback(
		(updated: Conversation[]) => {
			if (activeChatId && !updated.some((c) => c.id === activeChatId)) {
				setActiveChatId(updated[0]?.id ?? null);
			}
			refreshConversations();
		},
		[activeChatId, refreshConversations],
	);

	const handleSend = async (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = input.trim();
		if (!trimmed || isLoading) return;

		let conversationId = activeChatId;
		if (!conversationId) {
			const created = await createConversation(
				trimmed.slice(0, 40) || "New Conversation",
			);
			if (!created) {
				toast.error("Could not create conversation");
				return;
			}
			conversationId = created.id;
			setActiveChatId(created.id);
		}

		const tempUser: Message = {
			id: `tmp-user-${Date.now()}`,
			conversation_id: conversationId,
			role: "user",
			content: trimmed,
			created_at: new Date().toISOString(),
		};
		addMessage(tempUser);
		setInput("");

		try {
			const result = await submit({
				question: trimmed,
				conversation_id: conversationId,
				voice_mode: false,
				response_style: style,
			});
			if (!result) return;
			refreshMessages();
		} catch (err) {
			toast.error(
				err instanceof Error ? err.message : "Query failed",
			);
		}
	};

	return (
		<div className="flex h-screen bg-background text-foreground">
			<ChatSidebar
				activeChatId={activeChatId ?? undefined}
				onSelectChat={handleSelectChat}
				conversations={conversations}
				onConversationsChange={handleChatsChange}
			/>

			<main className="flex-1 flex flex-col">
				<header className="h-14 border-b border-border px-4 flex items-center justify-between shrink-0">
					<p className="text-sm font-medium truncate">
						{activeConversation?.title ?? "New chat"}
					</p>
					<div className="flex gap-1">
						{STYLES.map((s) => (
							<button
								key={s.value}
								type="button"
								onClick={() => setStyle(s.value)}
								className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${
									style === s.value
										? "bg-primary text-primary-foreground"
										: "text-muted-foreground hover:bg-muted"
								}`}
							>
								{s.label}
							</button>
						))}
					</div>
				</header>

				<div className="flex-1 overflow-y-auto p-4 space-y-4">
					{!activeChatId ? (
						<div className="h-full flex items-center justify-center text-muted-foreground text-sm">
							Select a chat or type below to start
						</div>
					) : messages.length === 0 && !isLoading ? (
						<div className="h-full flex items-center justify-center text-muted-foreground text-sm">
							Start a conversation
						</div>
					) : (
						messages.map((msg) => (
							<div
								key={msg.id}
								className={`flex ${
									msg.role === "user"
										? "justify-end"
										: "justify-start"
								}`}
							>
								<div
									className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
										msg.role === "user"
											? "bg-primary text-primary-foreground"
											: "bg-muted text-foreground"
									}`}
								>
									{msg.content}
									{msg.sources && msg.sources.length > 0 && (
										<div className="mt-2 pt-2 border-t border-border/40 text-xs opacity-70">
											{msg.sources.slice(0, 3).map((s, i) => (
												<div key={i} className="truncate">
													{s.filename}
													{s.page_number
														? ` · p.${s.page_number}`
														: ""}
												</div>
											))}
										</div>
									)}
								</div>
							</div>
						))
					)}
					{isLoading && (
						<div className="flex justify-start">
							<div className="bg-muted rounded-2xl px-4 py-2 text-sm text-muted-foreground animate-pulse">
								Thinking…
							</div>
						</div>
					)}
				</div>

				<form
					onSubmit={handleSend}
					className="p-4 border-t border-border flex items-center gap-2"
				>
					<Input
						type="text"
						placeholder="Type a message..."
						value={input}
						onChange={(e) => setInput(e.target.value)}
						className="flex-1 rounded-xl h-10 px-3 text-sm"
						disabled={isLoading}
					/>
					<Button
						type="submit"
						size="icon"
						disabled={!input.trim() || isLoading}
						className="h-10 w-10 shrink-0 rounded-xl"
					>
						<PaperPlaneRight className="size-4" />
					</Button>
				</form>
			</main>
		</div>
	);
}
