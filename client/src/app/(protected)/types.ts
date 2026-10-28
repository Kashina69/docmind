export interface ChatSession {
	id: string;
	title: string;
	projectId?: string | null;
}

export interface Project {
	id: string;
	name: string;
}
