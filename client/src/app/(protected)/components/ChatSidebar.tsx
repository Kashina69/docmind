"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ConfirmationModal } from "@/components/global";
import {
	Check,
	ChevronDown,
	ChevronRight,
	Folder,
	Pencil,
	Trash,
	X,
} from "@/components/icons";
import { Button, Input } from "@/components/ui";
import { supabase } from "@/lib/supabase";
import type { ChatSession, Project } from "../types";
import { initialChats, initialProjects } from "../types";

interface ChatSidebarProps {
	activeChatId?: string;
	onSelectChat?: (chatId: string) => void;
	chats?: ChatSession[];
	onChatsChange?: (chats: ChatSession[]) => void;
}

export function ChatSidebar({
	activeChatId,
	onSelectChat,
	chats: controlledChats,
	onChatsChange,
}: ChatSidebarProps) {
	const router = useRouter();

	// Local state if not controlled externally
	const [internalChats, setInternalChats] =
		useState<ChatSession[]>(initialChats);
	const [projects, setProjects] = useState<Project[]>(initialProjects);

	// Collapsible project folders (expanded by default)
	const [openProjects, setOpenProjects] = useState<Record<string, boolean>>({
		"proj-1": true,
		"proj-2": true,
	});

	// Project deletion modal state
	const [projectToDelete, setProjectToDelete] = useState<Project | null>(
		null,
	);

	// New project inline creation
	const [isCreatingProject, setIsCreatingProject] = useState(false);
	const [newProjectName, setNewProjectName] = useState("");

	const toggleProject = (projectId: string) => {
		setOpenProjects((prev) => ({
			...prev,
			[projectId]:
				prev[projectId] === undefined ? false : !prev[projectId],
		}));
	};

	// Chat inline rename
	const [editingChatId, setEditingChatId] = useState<string | null>(null);
	const [editingTitle, setEditingTitle] = useState("");

	// Chat project assigning dropdown / popup
	const [assigningChatId, setAssigningChatId] = useState<string | null>(null);

	const chats = controlledChats ?? internalChats;

	const updateChats = (updated: ChatSession[]) => {
		if (onChatsChange) {
			onChatsChange(updated);
		} else {
			setInternalChats(updated);
		}
	};

	const handleNewChat = (projectId?: string | null) => {
		const newId = Date.now().toString();
		const newChat: ChatSession = {
			id: newId,
			title: "New chat",
			projectId: projectId ?? null,
		};
		const nextChats = [newChat, ...chats];
		updateChats(nextChats);

		if (onSelectChat) {
			onSelectChat(newId);
		} else {
			router.push("/chat");
		}
	};

	const handleSelect = (id: string) => {
		if (onSelectChat) {
			onSelectChat(id);
		} else {
			router.push("/chat");
		}
	};

	// Rename Chat
	const startEditing = (chat: ChatSession, e: React.MouseEvent) => {
		e.stopPropagation();
		setEditingChatId(chat.id);
		setEditingTitle(chat.title);
	};

	const saveEditing = (chatId: string, e?: React.FormEvent) => {
		if (e) e.preventDefault();
		const trimmed = editingTitle.trim();
		if (trimmed) {
			updateChats(
				chats.map((c) =>
					c.id === chatId ? { ...c, title: trimmed } : c,
				),
			);
		}
		setEditingChatId(null);
	};

	const cancelEditing = (e?: React.MouseEvent) => {
		if (e) e.stopPropagation();
		setEditingChatId(null);
	};

	// Delete Chat
	const handleDeleteChat = (chatId: string, e: React.MouseEvent) => {
		e.stopPropagation();
		const remaining = chats.filter((c) => c.id !== chatId);
		updateChats(remaining);
		if (activeChatId === chatId && remaining.length > 0) {
			handleSelect(remaining[0].id);
		}
	};

	// Delete Project and its chats
	const confirmDeleteProject = () => {
		if (!projectToDelete) return;

		const projectId = projectToDelete.id;
		// Delete all chats in the project
		const remainingChats = chats.filter((c) => c.projectId !== projectId);
		updateChats(remainingChats);

		// Delete project
		setProjects((prev) => prev.filter((p) => p.id !== projectId));

		// If current active chat was deleted, switch to first remaining chat
		if (
			chats.some(
				(c) => c.id === activeChatId && c.projectId === projectId,
			)
		) {
			if (remainingChats.length > 0) {
				handleSelect(remainingChats[0].id);
			}
		}

		setProjectToDelete(null);
	};

	// Create Project
	const handleCreateProject = (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = newProjectName.trim();
		if (!trimmed) return;

		const newProject: Project = {
			id: `proj-${Date.now()}`,
			name: trimmed,
		};
		setProjects((prev) => [...prev, newProject]);
		setNewProjectName("");
		setIsCreatingProject(false);
	};

	// Assign or remove chat to/from project
	const handleSetChatProject = (chatId: string, projectId: string | null) => {
		updateChats(
			chats.map((c) => (c.id === chatId ? { ...c, projectId } : c)),
		);
		setAssigningChatId(null);
	};

	const handleSignOut = async () => {
		await supabase.auth.signOut();
		router.push("/login");
	};

	// Filter chats by unassigned vs project
	const unassignedChats = chats.filter((c) => !c.projectId);

	return (
		<aside className="w-64 border-r border-border bg-card flex flex-col justify-between p-3 shrink-0 h-full select-none text-foreground">
			<div className="flex flex-col gap-3 overflow-hidden flex-1">
				{/* Chats Header & New Chat button */}
				<div className="flex items-center justify-between px-1">
					<h2 className="font-semibold text-sm">Chats</h2>
					<Button
						variant="outline"
						size="sm"
						onClick={() => handleNewChat()}
						className="text-xs h-7 px-2"
					>
						+ New
					</Button>
				</div>

				{/* Scrollable list of Projects and Chats */}
				<div className="flex flex-col gap-3 overflow-y-auto pr-1 flex-1 text-xs">
					{/* Projects Section */}
					<div className="space-y-1.5">
						<div className="flex items-center justify-between text-muted-foreground px-1 py-0.5">
							<span className="font-semibold uppercase tracking-wider text-[10px]">
								Projects
							</span>
							<button
								type="button"
								onClick={() => setIsCreatingProject((v) => !v)}
								className="text-primary hover:underline font-medium text-[11px]"
							>
								+ Project
							</button>
						</div>

						{/* Inline Project Creator */}
						{isCreatingProject && (
							<form
								onSubmit={handleCreateProject}
								className="flex gap-1 px-1"
							>
								<Input
									type="text"
									placeholder="Project name"
									value={newProjectName}
									onChange={(e) =>
										setNewProjectName(e.target.value)
									}
									className="h-7 text-xs flex-1 rounded-lg"
									autoFocus
								/>
								<Button
									type="submit"
									size="sm"
									className="h-7 px-2 text-xs"
								>
									Add
								</Button>
								<Button
									type="button"
									variant="ghost"
									size="sm"
									onClick={() => setIsCreatingProject(false)}
									className="h-7 px-1.5 text-xs text-muted-foreground"
								>
									<X className="size-3.5" />
								</Button>
							</form>
						)}

						{/* Project List with nested chats */}
						{projects.map((project) => {
							const projectChats = chats.filter(
								(c) => c.projectId === project.id,
							);
							const isOpen = openProjects[project.id] ?? true;

							return (
								<div key={project.id} className="space-y-0.5">
									<div className="flex items-center justify-between px-2 py-1 text-muted-foreground group rounded-lg hover:bg-muted/40 transition-colors">
										<button
											type="button"
											onClick={() =>
												toggleProject(project.id)
											}
											className="flex items-center gap-1.5 font-medium truncate flex-1 text-left"
										>
											{isOpen ? (
												<ChevronDown className="size-3 shrink-0 text-muted-foreground/70" />
											) : (
												<ChevronRight className="size-3 shrink-0 text-muted-foreground/70" />
											)}
											<Folder className="size-3.5 shrink-0 text-muted-foreground" />
											<span className="truncate">
												{project.name}
											</span>
											<span className="text-[10px] text-muted-foreground/50 ml-auto mr-1">
												({projectChats.length})
											</span>
										</button>

										<div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
											<button
												type="button"
												onClick={() =>
													handleNewChat(project.id)
												}
												className="text-[10px] text-muted-foreground hover:text-foreground px-1"
												title="New chat in this project"
											>
												+
											</button>
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													setProjectToDelete(project);
												}}
												className="p-1 text-muted-foreground hover:text-rose-400 transition-colors"
												title="Delete project"
											>
												<Trash className="size-3" />
											</button>
										</div>
									</div>

									{/* Chats inside this project (collapsible dropdown) */}
									{isOpen && (
										<div className="pl-3.5 space-y-0.5 border-l border-border/40 ml-3">
											{projectChats.length === 0 ? (
												<p className="text-[10px] text-muted-foreground/50 px-2 py-1 italic">
													No chats
												</p>
											) : (
												projectChats.map((chat) => (
													<ChatItemRow
														key={chat.id}
														chat={chat}
														projects={projects}
														isActive={
															activeChatId ===
															chat.id
														}
														isEditing={
															editingChatId ===
															chat.id
														}
														isAssigning={
															assigningChatId ===
															chat.id
														}
														editingTitle={
															editingTitle
														}
														onSelect={() =>
															handleSelect(
																chat.id,
															)
														}
														onStartEdit={(e) =>
															startEditing(
																chat,
																e,
															)
														}
														onSaveEdit={(e) =>
															saveEditing(
																chat.id,
																e,
															)
														}
														onCancelEdit={
															cancelEditing
														}
														onEditingTitleChange={
															setEditingTitle
														}
														onDelete={(e) =>
															handleDeleteChat(
																chat.id,
																e,
															)
														}
														onToggleAssign={(e) => {
															e.stopPropagation();
															setAssigningChatId(
																(prev) =>
																	prev ===
																	chat.id
																		? null
																		: chat.id,
															);
														}}
														onSetProject={(
															projId,
														) =>
															handleSetChatProject(
																chat.id,
																projId,
															)
														}
													/>
												))
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>

					{/* Unassigned / Direct Chats */}
					<div className="space-y-0.5 pt-1">
						<div className="text-muted-foreground px-1 py-0.5 font-semibold uppercase tracking-wider text-[10px]">
							Direct Chats
						</div>
						{unassignedChats.length === 0 ? (
							<p className="text-[11px] text-muted-foreground/60 px-2 py-1">
								No individual chats
							</p>
						) : (
							unassignedChats.map((chat) => (
								<ChatItemRow
									key={chat.id}
									chat={chat}
									projects={projects}
									isActive={activeChatId === chat.id}
									isEditing={editingChatId === chat.id}
									isAssigning={assigningChatId === chat.id}
									editingTitle={editingTitle}
									onSelect={() => handleSelect(chat.id)}
									onStartEdit={(e) => startEditing(chat, e)}
									onSaveEdit={(e) => saveEditing(chat.id, e)}
									onCancelEdit={cancelEditing}
									onEditingTitleChange={setEditingTitle}
									onDelete={(e) =>
										handleDeleteChat(chat.id, e)
									}
									onToggleAssign={(e) => {
										e.stopPropagation();
										setAssigningChatId((prev) =>
											prev === chat.id ? null : chat.id,
										);
									}}
									onSetProject={(projId) =>
										handleSetChatProject(chat.id, projId)
									}
								/>
							))
						)}
					</div>
				</div>
			</div>

			{/* Sign Out Button */}
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

			{/* Project Deletion Confirmation Modal */}
			<ConfirmationModal
				isOpen={projectToDelete !== null}
				title={`Delete "${projectToDelete?.name}"?`}
				description="Do you want to delete this project? The chats in it will also be deleted."
				confirmLabel="Delete Project"
				cancelLabel="Cancel"
				variant="destructive"
				onConfirm={confirmDeleteProject}
				onClose={() => setProjectToDelete(null)}
			/>
		</aside>
	);
}

// Subcomponent for each chat row with edit, delete, and project assignment
function ChatItemRow({
	chat,
	projects,
	isActive,
	isEditing,
	isAssigning,
	editingTitle,
	onSelect,
	onStartEdit,
	onSaveEdit,
	onCancelEdit,
	onEditingTitleChange,
	onDelete,
	onToggleAssign,
	onSetProject,
}: {
	chat: ChatSession;
	projects: Project[];
	isActive: boolean;
	isEditing: boolean;
	isAssigning: boolean;
	editingTitle: string;
	onSelect: () => void;
	onStartEdit: (e: React.MouseEvent) => void;
	onSaveEdit: (e?: React.FormEvent) => void;
	onCancelEdit: (e?: React.MouseEvent) => void;
	onEditingTitleChange: (v: string) => void;
	onDelete: (e: React.MouseEvent) => void;
	onToggleAssign: (e: React.MouseEvent) => void;
	onSetProject: (projId: string | null) => void;
}) {
	if (isEditing) {
		return (
			<form
				onSubmit={onSaveEdit}
				className="flex items-center gap-1 px-1 py-0.5"
			>
				<Input
					type="text"
					value={editingTitle}
					onChange={(e) => onEditingTitleChange(e.target.value)}
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
					onClick={onCancelEdit}
					className="text-muted-foreground hover:text-foreground p-0.5"
					title="Cancel"
				>
					<X className="size-3.5" />
				</button>
			</form>
		);
	}

	return (
		<div className="relative group flex items-center justify-between rounded-lg px-2.5 py-1 text-xs transition-colors hover:bg-muted/50">
			<button
				type="button"
				onClick={onSelect}
				className={`flex-1 text-left truncate py-0.5 cursor-pointer ${
					isActive
						? "font-medium text-foreground"
						: "text-muted-foreground hover:text-foreground"
				}`}
			>
				{chat.title}
			</button>

			{/* Action icons on hover */}
			<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
				{/* Project folder assign / remove icon */}
				<button
					type="button"
					onClick={onToggleAssign}
					className="p-0.5 text-muted-foreground hover:text-foreground"
					title="Move to project"
				>
					<Folder className="size-3" />
				</button>

				{/* Edit icon */}
				<button
					type="button"
					onClick={onStartEdit}
					className="p-0.5 text-muted-foreground hover:text-foreground"
					title="Rename chat"
				>
					<Pencil className="size-3" />
				</button>

				{/* Delete icon */}
				<button
					type="button"
					onClick={onDelete}
					className="p-0.5 text-muted-foreground hover:text-rose-400"
					title="Delete chat"
				>
					<Trash className="size-3" />
				</button>
			</div>

			{/* Project selector popover dropdown */}
			{isAssigning && (
				<div className="absolute left-4 right-4 top-full mt-1 z-20 bg-card border border-border rounded-xl p-1.5 shadow-xl space-y-1">
					<p className="text-[10px] font-semibold text-muted-foreground px-1 pb-0.5 border-b border-border/40">
						Assign Project
					</p>
					{chat.projectId && (
						<button
							type="button"
							onClick={() => onSetProject(null)}
							className="w-full text-left px-2 py-1 text-[11px] rounded hover:bg-muted text-rose-400"
						>
							Remove from project
						</button>
					)}
					{projects.map((p) => (
						<button
							key={p.id}
							type="button"
							onClick={() => onSetProject(p.id)}
							className={`w-full text-left px-2 py-1 text-[11px] rounded hover:bg-muted truncate ${
								chat.projectId === p.id
									? "bg-muted font-medium text-foreground"
									: "text-muted-foreground"
							}`}
						>
							{p.name}
						</button>
					))}
				</div>
			)}
		</div>
	);
}
