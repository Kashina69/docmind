"use client";

import { useCallback, useEffect, useState } from "react";
import type { Document } from "@/lib/types";
import { supabaseFetch } from "@/lib/supabase";
import {
	deleteDocumentApi,
	uploadDocumentDirect,
} from "@/services/documents";

interface UseDocumentsReturn {
	documents: Document[];
	loading: boolean;
	error: string | null;
	uploadDocument: (file: File) => Promise<Document | null>;
	deleteDocument: (id: string) => Promise<boolean>;
	refresh: () => void;
}

const POLL_INTERVAL_MS = 5000;
const ACTIVE_STATUSES: Document["status"][] = ["processing", "indexing"];

export function useDocuments(): UseDocumentsReturn {
	const [documents, setDocuments] = useState<Document[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchDocuments = useCallback(async () => {
		try {
			const data = await supabaseFetch<Document[]>(
				"documents?order=created_at.desc",
			);
			setDocuments(data);
			setError(null);
			return data;
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to load documents",
			);
			return [];
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchDocuments();
	}, [fetchDocuments]);

	useEffect(() => {
		if (!documents.some((d) => ACTIVE_STATUSES.includes(d.status))) {
			return;
		}
		const timer = setInterval(() => {
			fetchDocuments();
		}, POLL_INTERVAL_MS);
		return () => clearInterval(timer);
	}, [documents, fetchDocuments]);

	const uploadDocument = useCallback(
		async (file: File): Promise<Document | null> => {
			try {
				await uploadDocumentDirect(file);
				await fetchDocuments();
				const latest = await supabaseFetch<Document[]>(
					"documents?order=created_at.desc&limit=1",
				);
				return latest[0] ?? null;
			} catch (err) {
				console.error("Failed to upload document:", err);
				return null;
			}
		},
		[fetchDocuments],
	);

	const deleteDocument = useCallback(async (id: string): Promise<boolean> => {
		const previous = documents;
		setDocuments((prev) => prev.filter((d) => d.id !== id));
		try {
			await deleteDocumentApi(id);
			return true;
		} catch (err) {
			console.error("Failed to delete document:", err);
			setDocuments(previous);
			return false;
		}
	}, [documents]);

	return {
		documents,
		loading,
		error,
		uploadDocument,
		deleteDocument,
		refresh: fetchDocuments,
	};
}
