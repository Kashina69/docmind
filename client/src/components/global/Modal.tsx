"use client";

import { X } from "@/components/icons";

export interface ModalProps {
	isOpen: boolean;
	onClose: () => void;
	title?: string;
	description?: string;
	children: React.ReactNode;
	maxWidthClass?: string;
}

export function Modal({
	isOpen,
	onClose,
	title,
	description,
	children,
	maxWidthClass = "max-w-xl",
}: ModalProps) {
	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
			{/* Backdrop click to dismiss */}
			<button
				type="button"
				aria-label="Close modal"
				className="fixed inset-0 cursor-default bg-transparent border-0"
				onClick={onClose}
			/>

			<div
				role="dialog"
				aria-modal="true"
				className={`relative z-10 w-full ${maxWidthClass} rounded-2xl bg-card border border-border p-6 shadow-2xl text-foreground`}
			>
				<button
					type="button"
					onClick={onClose}
					className="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
				>
					<X className="size-4" />
				</button>

				{(title || description) && (
					<div className="mb-5">
						{title && (
							<h2 className="text-base font-semibold text-foreground">
								{title}
							</h2>
						)}
						{description && (
							<p className="text-xs text-muted-foreground mt-1">
								{description}
							</p>
						)}
					</div>
				)}

				{children}
			</div>
		</div>
	);
}
