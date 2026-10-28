"use client";

import { useState } from "react";
import { ArrowPathIcon, TrashIcon, UploadIcon } from "@/components/icons";
import { Button, toast } from "@/components/ui";
import { useDocuments } from "@/hooks/useDocuments";
import type { Document } from "@/lib/types";
import { ChatSidebar } from "../components/ChatSidebar";
import { DocumentCard } from "./components/DocumentCard";
import { DocumentStatusBanner } from "./components/DocumentStatusBanner";
import { UploadModal } from "./components/UploadModal";

function formatDate(iso: string): string {
	try {
		return new Date(iso).toLocaleDateString(undefined, {
			month: "short",
			day: "numeric",
			year: "numeric",
		});
	} catch {
		return "";
	}
}

export default function DashboardPage() {
	const { documents, loading, uploadDocument, deleteDocument, refresh } =
		useDocuments();
	const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
	const [uploading, setUploading] = useState(false);
	const [confirmDelete, setConfirmDelete] = useState<Document | null>(null);

	const processingCount = documents.filter((d) =>
		["processing", "indexing"].includes(d.status),
	).length;
	const failedCount = documents.filter((d) => d.status === "failed").length;

	const handleFilesUpload = async (files: File[]) => {
		const pdfs = files.filter(
			(f) => f.type === "application/pdf" || f.name.endsWith(".pdf"),
		);
		if (pdfs.length === 0) {
			toast.error("Only PDF files are supported");
			return;
		}
		if (pdfs.length !== files.length) {
			toast.error("Skipped non-PDF files");
		}
		setUploading(true);
		let ok = 0;
		for (const file of pdfs) {
			const doc = await uploadDocument(file);
			if (doc) ok++;
		}
		setUploading(false);
		setIsUploadModalOpen(false);
		if (ok > 0) {
			toast.success(
				`Uploaded ${ok} document${ok > 1 ? "s" : ""} — processing…`,
			);
		} else {
			toast.error("Upload failed");
		}
	};

	const handleConfirmDelete = async () => {
		if (!confirmDelete) return;
		const doc = confirmDelete;
		setConfirmDelete(null);
		const success = await deleteDocument(doc.id);
		if (success) {
			toast.success(`Deleted ${doc.filename}`);
		} else {
			toast.error("Delete failed");
		}
	};

	return (
		<div className="flex h-screen bg-background text-foreground">
			<ChatSidebar />

			<main className="flex-1 flex flex-col h-full overflow-hidden">
				<header className="h-16 border-b border-border px-6 flex items-center justify-between shrink-0">
					<div>
						<h1 className="text-lg font-semibold text-foreground">
							Your Documents
						</h1>
					</div>

					<div className="flex items-center gap-2">
						<Button
							variant="outline"
							size="sm"
							onClick={refresh}
							disabled={loading}
							className="gap-1.5"
						>
							<ArrowPathIcon
								className={`size-4 ${loading ? "animate-spin" : ""}`}
							/>
							Reload
						</Button>

						<Button
							size="sm"
							onClick={() => setIsUploadModalOpen(true)}
							className="gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground"
						>
							<UploadIcon className="size-4" />
							Upload
						</Button>
					</div>
				</header>

				<div className="flex-1 overflow-y-auto p-6 space-y-6">
					<DocumentStatusBanner
						totalCount={documents.length}
						processingCount={processingCount}
						failedCount={failedCount}
					/>

					{loading && documents.length === 0 ? (
						<div className="text-center py-12 text-sm text-muted-foreground">
							Loading documents…
						</div>
					) : documents.length === 0 ? (
						<div className="text-center py-12 text-sm text-muted-foreground">
							No documents yet. Click Upload to add your first
							document.
						</div>
					) : (
						<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{documents.map((doc) => (
								<div key={doc.id} className="relative group">
									<DocumentCard
										document={doc}
										date={formatDate(doc.created_at)}
									/>
									<button
										type="button"
										onClick={() => setConfirmDelete(doc)}
										title="Delete document"
										className="absolute top-2 right-2 p-1.5 rounded-lg bg-background/80 border border-border text-muted-foreground hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity"
									>
										<TrashIcon className="size-3.5" />
									</button>
								</div>
							))}
						</div>
					)}
				</div>
			</main>

			<UploadModal
				isOpen={isUploadModalOpen}
				onClose={() => setIsUploadModalOpen(false)}
				onUpload={handleFilesUpload}
				uploading={uploading}
				documents={documents}
			/>

			{confirmDelete && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
					<div className="bg-card border border-border rounded-2xl p-6 max-w-sm w-full space-y-4">
						<h3 className="font-semibold">Delete document?</h3>
						<p className="text-sm text-muted-foreground break-all">
							{confirmDelete.filename} will be permanently
							deleted with all its chunks.
						</p>
						<div className="flex gap-2 justify-end">
							<Button
								variant="outline"
								size="sm"
								onClick={() => setConfirmDelete(null)}
							>
								Cancel
							</Button>
							<Button
								variant="destructive"
								size="sm"
								onClick={handleConfirmDelete}
							>
								Delete
							</Button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
