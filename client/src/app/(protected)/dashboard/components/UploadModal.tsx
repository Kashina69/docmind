"use client";

import { Modal } from "@/components/global";
import type { DocumentItem } from "../data";
import { DocumentList } from "./DocumentList";
import { UploadDropzone } from "./UploadDropzone";

interface UploadModalProps {
	isOpen: boolean;
	onClose: () => void;
	onUpload: (files: File[]) => void;
	documents: DocumentItem[];
}

export function UploadModal({
	isOpen,
	onClose,
	onUpload,
	documents,
}: UploadModalProps) {
	return (
		<Modal
			isOpen={isOpen}
			onClose={onClose}
			title="Upload a PDF"
			description="Upload your documents to make them searchable with AI. Supported: PDF · Max 50MB"
			maxWidthClass="max-w-xl"
		>
			<div className="space-y-6">
				{/* Upload document dropzone section at top */}
				<UploadDropzone onFilesSelected={onUpload} />

				{/* Reusable Documents list section at bottom */}
				<DocumentList documents={documents} />
			</div>
		</Modal>
	);
}
