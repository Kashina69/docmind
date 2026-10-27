"use client";

import { useState } from "react";
import { ArrowPathIcon, UploadIcon } from "@/components/icons";
import { Button, toast } from "@/components/ui";
import { ChatSidebar } from "../components/ChatSidebar";
import { DocumentCard } from "./components/DocumentCard";
import { DocumentStatusBanner } from "./components/DocumentStatusBanner";
import { UploadModal } from "./components/UploadModal";
import { type DocumentItem, initialDocuments } from "./data";

export default function DashboardPage() {
	const [documents, setDocuments] =
		useState<DocumentItem[]>(initialDocuments);
	const [isRefreshing, setIsRefreshing] = useState(false);
	const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

	const processingCount = documents.filter(
		(d) => d.status === "processing",
	).length;
	const failedCount = documents.filter((d) => d.status === "failed").length;

	const handleRefresh = () => {
		setIsRefreshing(true);
		setTimeout(() => {
			// Simulate reload / status updates
			setDocuments([...initialDocuments]);
			setIsRefreshing(false);
			toast.success("Documents refreshed");
		}, 600);
	};

	const handleFilesUpload = (files: File[]) => {
		const newDocs: DocumentItem[] = files.map((file, idx) => {
			const ext = file.name.split(".").pop()?.toUpperCase() || "PDF";
			return {
				id: `doc-${Date.now()}-${idx}`,
				name: file.name,
				type: ext,
				date: "Just now",
				status: "processing" as const,
			};
		});

		setDocuments((prev) => [...newDocs, ...prev]);
		toast.success(
			`Uploaded ${files.length} document${files.length > 1 ? "s" : ""}`,
		);
	};

	return (
		<div className="flex h-screen bg-background text-foreground">
			{/* Left Sidebar: Shared Chat History */}
			<ChatSidebar />

			{/* Right Content: Documents Dashboard */}
			<main className="flex-1 flex flex-col h-full overflow-hidden">
				{/* Top Header */}
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
							onClick={handleRefresh}
							disabled={isRefreshing}
							className="gap-1.5"
						>
							<ArrowPathIcon
								className={`size-4 ${isRefreshing ? "animate-spin" : ""}`}
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

				{/* Content Body */}
				<div className="flex-1 overflow-y-auto p-6 space-y-6">
					{/* Status Banner Component */}
					<DocumentStatusBanner
						totalCount={documents.length}
						processingCount={processingCount}
						failedCount={failedCount}
					/>

					{/* Documents Grid */}
					{documents.length === 0 ? (
						<div className="text-center py-12 text-sm text-muted-foreground">
							No documents yet. Click Upload to add your first
							document.
						</div>
					) : (
						<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{documents.map((doc) => (
								<DocumentCard key={doc.id} document={doc} />
							))}
						</div>
					)}
				</div>
			</main>

			{/* Upload Modal */}
			<UploadModal
				isOpen={isUploadModalOpen}
				onClose={() => setIsUploadModalOpen(false)}
				onUpload={handleFilesUpload}
				documents={documents}
			/>
		</div>
	);
}
