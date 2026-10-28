import { backendFetch } from "./api";

export interface UploadResult {
	status: string;
	document_id: string;
}

export async function uploadDocumentDirect(file: File): Promise<UploadResult> {
	const { getAccessToken } = await import("@/lib/supabase");
	const token = await getAccessToken();
	const { API_BASE_URL } = await import("./api");

	const form = new FormData();
	form.append("file", file);

	const res = await fetch(`${API_BASE_URL}/documents/upload`, {
		method: "POST",
		headers: token ? { Authorization: `Bearer ${token}` } : {},
		body: form,
	});

	if (!res.ok) {
		const text = await res.text().catch(() => "Unknown error");
		throw new Error(`Upload failed ${res.status}: ${text}`);
	}

	return res.json();
}

export function deleteDocumentApi(id: string): Promise<{ deleted: boolean }> {
	return backendFetch<{ deleted: boolean }>(`/documents/${id}`, {
		method: "DELETE",
	});
}

export function getDocumentUrlApi(
	document_id: string,
): Promise<{ document_url: string; filename: string }> {
	return backendFetch(`/document-url`, { params: { document_id } });
}
