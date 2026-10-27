export interface ChatSession {
	id: string;
	title: string;
	projectId?: string | null;
}

export interface Project {
	id: string;
	name: string;
}

export const initialProjects: Project[] = [
	{ id: "proj-1", name: "General" },
	{ id: "proj-2", name: "Research" },
];

export const initialChats: ChatSession[] = [
	{ id: "1", title: "New chat", projectId: null },
];
