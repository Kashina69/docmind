"use client";

import { useState } from "react";
import { PaperPlaneRight } from "@/components/icons";
import { Button, Input } from "@/components/ui";
import { ChatSidebar } from "../components/ChatSidebar";
import type { ChatSession } from "../types";
import { initialChats } from "../types";

interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
}

export default function ChatPage() {
	const [chats, setChats] = useState<ChatSession[]>(initialChats);
	const [activeChatId, setActiveChatId] = useState<string>("1");
	const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({
		"1": [],
	});
	const [input, setInput] = useState("");

	const currentMessages = messages[activeChatId] || [];

	const handleSend = (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = input.trim();
		if (!trimmed) return;

		const userMsg: ChatMessage = {
			id: Date.now().toString(),
			role: "user",
			content: trimmed,
		};

		setMessages((prev) => ({
			...prev,
			[activeChatId]: [...(prev[activeChatId] || []), userMsg],
		}));
		setInput("");

		// Update conversation title if it is still default
		setChats((prev) =>
			prev.map((c) =>
				c.id === activeChatId && c.title === "New chat"
					? { ...c, title: trimmed.slice(0, 24) }
					: c,
			),
		);
	};

	return (
		<div className="flex h-screen bg-background text-foreground">
			{/* Left Sidebar: Shared Chat History with rename, delete & projects */}
			<ChatSidebar
				activeChatId={activeChatId}
				onSelectChat={setActiveChatId}
				chats={chats}
				onChatsChange={setChats}
			/>

			{/* Right: Chat Area */}
			<main className="flex-1 flex flex-col">
				{/* Messages */}
				<div className="flex-1 overflow-y-auto p-4 space-y-4">
					{currentMessages.length === 0 ? (
						<div className="h-full flex items-center justify-center text-muted-foreground text-sm">
							Start a conversation
						</div>
					) : (
						currentMessages.map((msg) => (
							<div
								key={msg.id}
								className={`flex ${
									msg.role === "user"
										? "justify-end"
										: "justify-start"
								}`}
							>
								<div
									className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
										msg.role === "user"
											? "bg-primary text-primary-foreground"
											: "bg-muted text-foreground"
									}`}
								>
									{msg.content}
								</div>
							</div>
						))
					)}
				</div>

				{/* Input Area */}
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
					/>
					<Button
						type="submit"
						size="icon"
						disabled={!input.trim()}
						className="h-10 w-10 shrink-0 rounded-xl"
					>
						<PaperPlaneRight className="size-4" />
					</Button>
				</form>
			</main>
		</div>
	);
}
