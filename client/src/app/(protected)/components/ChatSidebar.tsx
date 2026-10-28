"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ConfirmationModal } from "@/components/global";
import { Check, Pencil, Trash, X } from "@/components/icons";
import { Button, Input, toast } from "@/components/ui";
import { useConversations } from "@/hooks/useConversations";
import { supabase, supabaseFetch } from "@/lib/supabase";
import type { Conversation } from "@/lib/types";
import { deleteConversationApi } from "@/services/conversations";

interface ChatSidebarProps {
	activeChatId?: string;
	onSelectChat?: (chatId: string) => void;
	conversations?: Conversation[];
	onConversationsChange?: (conversations: Conversation[]) => void;
}

export function ChatSidebar({
	activeChatId,
	onSelectChat,
	conversations: controlledConversations,
	onConversationsChange,
}: ChatSidebarProps) {
	const router = useRouter();
	const hook = useConversations();
	const conversations = controlledConversations ?? hook.conversations;

	const [editingChatId, setEditingChatId] = useState<string | null>(null);
	const [editingTitle, setEditingTitle] = useState("");
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(
		null,
	);
	const [creating, setCreating] = useState(false);

	const handleSelect = (id: string) => {
		if (onSelectChat) {
			onSelectChat(id);
		} else {
			router.push("/chat");
		}
	};

	const handleNewChat = async () => {
		if (creating) return;
		setCreating(true);
		const created = await hook.createConversation("New Conversation");
		setCreating(false);
		if (created) {
			onConversationsChange?.([created, ...conversations]);
			handleSelect(created.id);
		} else {
			toast.error("Could not create conversation");
		}
	};

	const startEditing = (chat: Conversation, e: React.MouseEvent) => {
		e.stopPropagation();
		setEditingChatId(chat.id);
		setEditingTitle(chat.title);
	};

	const saveEditing = async (chatId: string, e?: React.FormEvent) => {
		if (e) e.preventDefault();
		const trimmed = editingTitle.trim();
		setEditingChatId(null);
		if (!trimmed) return;
		try {
			await supabaseFetch("conversations", {
				method: "PATCH",
				body: JSON.stringify({ title: trimmed }),
			});
			onConversationsChange?.(
				conversations.map((c) =>
					c.id === chatId ? { ...c, title: trimmed } : c,
				),
			);
			hook.refresh();
		} catch {
			toast.error("Rename failed");
		}
	};

	const cancelEditing = (e?: React.MouseEvent) => {
		if (e) e.stopPropagation();
		setEditingChatId(null);
	};

	const handleDeleteChat = (chatId: string, e: React.MouseEvent) => {
		e.stopPropagation();
		setConfirmDeleteId(chatId);
	};

	const confirmDelete = async () => {
		if (!confirmDeleteId) return;
		const chatId = confirmDeleteId;
		setConfirmDeleteId(null);
		try {
			await deleteConversationApi(chatId);
			const remaining = conversations.filter((c) => c.id !== chatId);
			onConversationsChange?.(remaining);
			hook.refresh();
			if (activeChatId === chatId && remaining.length > 0) {
				handleSelect(remaining[0].id);
			}
		} catch {
			toast.error("Delete failed");
		}
	};

	const handleSignOut = async () => {
		await supabase.auth.signOut();
		router.push("/login");
	};

	return (
		<aside className="w-64 border-r border-border bg-card flex flex-col justify-between p-3 shrink-0 h-full select-none text-foreground">
			<div className="flex flex-col gap-3 overflow-hidden flex-1">
				<div className="flex items-center justify-between px-1">
					<h2 className="font-semibold text-sm">Chats</h2>
					<Button
						variant="outline"
						size="sm"
						onClick={handleNewChat}
						disabled={creating}
						className="text-xs h-7 px-2"
					>
						+ New
					</Button>
				</div>

				<div className="flex flex-col gap-0.5 overflow-y-auto pr-1 flex-1 text-xs">
					{conversations.length === 0 ? (
						<p className="text-[11px] text-muted-foreground/60 px-2 py-1">
							No conversations yet
						</p>
					) : (
						conversations.map((chat) =>
							editingChatId === chat.id ? (
								<form
									key={chat.id}
									onSubmit={(e) => saveEditing(chat.id, e)}
									className="flex items-center gap-1 px-1 py-0.5"
								>
									<Input
										type="text"
										value={editingTitle}
										onChange={(e) =>
											setEditingTitle(e.target.value)
										}
										className="h-6 text-xs flex-1 rounded-md px-1.5"
										autoFocus
									/>
									<button
										type="submit"
										className="text-emerald-500 hover:text-emerald-400 p-0.5"
										title="Save"
									>
										<Check className="size-3.5" />
									</button>
									<button
										type="button"
										onClick={cancelEditing}
										className="text-muted-foreground hover:text-foreground p-0.5"
										title="Cancel"
									>
										<X className="size-3.5" />
									</button>
								</form>
							) : (
								<div
									key={chat.id}
									className="relative group flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition-colors hover:bg-muted/50"
								>
									<button
										type="button"
										onClick={() => handleSelect(chat.id)}
										className={`flex-1 text-left truncate py-0.5 cursor-pointer ${
											activeChatId === chat.id
												? "font-medium text-foreground"
												: "text-muted-foreground hover:text-foreground"
										}`}
									>
										{chat.title}
									</button>

									<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
										<button
											type="button"
											onClick={(e) =>
												startEditing(chat, e)
											}
											className="p-0.5 text-muted-foreground hover:text-foreground"
											title="Rename chat"
										>
											<Pencil className="size-3" />
										</button>
										<button
											type="button"
											onClick={(e) =>
												handleDeleteChat(chat.id, e)
											}
											className="p-0.5 text-muted-foreground hover:text-rose-400"
											title="Delete chat"
										>
											<Trash className="size-3" />
										</button>
									</div>
								</div>
							),
						)
					)}
				</div>
			</div>

			<div className="pt-2 border-t border-border/40 shrink-0">
				<Button
					variant="ghost"
					size="sm"
					onClick={handleSignOut}
					className="w-full justify-start text-xs text-muted-foreground hover:text-foreground"
				>
					Sign out
				</Button>
			</div>

			<ConfirmationModal
				isOpen={confirmDeleteId !== null}
				title="Delete this chat?"
				description="Messages in this conversation will be permanently deleted."
				confirmLabel="Delete"
				cancelLabel="Cancel"
				variant="destructive"
				onConfirm={confirmDelete}
				onClose={() => setConfirmDeleteId(null)}
			/>
		</aside>
	);
}
