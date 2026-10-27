"use client";

import { type ChangeEvent, type DragEvent, useRef, useState } from "react";
import { CloudArrowUp } from "@/components/icons";

interface UploadDropzoneProps {
	onFilesSelected: (files: File[]) => void;
	accept?: string;
	maxSizeLabel?: string;
}

export function UploadDropzone({
	onFilesSelected,
	accept = "application/pdf,.pdf",
	maxSizeLabel = "PDF only · Max 50MB",
}: UploadDropzoneProps) {
	const [isDragging, setIsDragging] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const handleDragOver = (e: DragEvent<HTMLElement>) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(true);
	};

	const handleDragLeave = (e: DragEvent<HTMLElement>) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);
	};

	const handleDrop = (e: DragEvent<HTMLElement>) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);

		const files = Array.from(e.dataTransfer.files).filter(
			(file) =>
				file.type === "application/pdf" || file.name.endsWith(".pdf"),
		);

		if (files.length > 0) {
			onFilesSelected(files);
		}
	};

	const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
		if (e.target.files && e.target.files.length > 0) {
			const files = Array.from(e.target.files);
			onFilesSelected(files);
			e.target.value = "";
		}
	};

	return (
		<div>
			<input
				ref={fileInputRef}
				type="file"
				accept={accept}
				multiple
				className="hidden"
				onChange={handleChange}
			/>

			<button
				type="button"
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				onDrop={handleDrop}
				onClick={() => fileInputRef.current?.click()}
				className={`w-full cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-colors flex flex-col items-center justify-center gap-2 ${
					isDragging
						? "border-primary bg-primary/10"
						: "border-border bg-muted/20 hover:border-border/80 hover:bg-muted/30"
				}`}
			>
				<CloudArrowUp className="size-8 text-primary" />
				<p className="text-sm text-foreground">
					Drop your PDF here or{" "}
					<span className="text-primary font-medium underline">
						browse
					</span>
				</p>
				<p className="text-xs text-muted-foreground">{maxSizeLabel}</p>
			</button>
		</div>
	);
}
