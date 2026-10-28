"use client";

import { Modal } from "@/components/global";
import type { DocumentItem } from "../data";
import { DocumentList } from "./DocumentList";
import { UploadDropzone } from "./UploadDropzone";

interface UploadModalProps {
	isOpen: boolean;
	onClose: () => void;
	onUpload: (files: File[]) => void;
	uploading?: boolean;
	documents: DocumentItem[];
}

export function UploadModal({
	isOpen,
	onClose,
	onUpload,
	uploading = false,
	documents,
}: UploadModalProps) {
	return (
		<Modal
			isOpen={isOpen}
			onClose={uploading ? () => {} : onClose}
			title="Upload a PDF"
			description="Upload your documents to make them searchable with AI. Supported: PDF · Max 50MB"
			maxWidthClass="max-w-xl"
		>
			<div className="space-y-6">
				<UploadDropzone onFilesSelected={onUpload} disabled={uploading} />

				{uploading && (
					<p className="text-xs text-muted-foreground text-center animate-pulse">
						Uploading… do not close
					</p>
				)}

				<DocumentList documents={documents} />
			</div>
		</Modal>
	);
}
