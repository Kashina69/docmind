"use client";

import { Button } from "@/components/ui";
import { Modal } from "./Modal";

interface ConfirmationModalProps {
	isOpen: boolean;
	title: string;
	description: string;
	confirmLabel?: string;
	cancelLabel?: string;
	variant?: "destructive" | "default";
	onConfirm: () => void;
	onClose: () => void;
}

export function ConfirmationModal({
	isOpen,
	title,
	description,
	confirmLabel = "Delete",
	cancelLabel = "Cancel",
	variant = "destructive",
	onConfirm,
	onClose,
}: ConfirmationModalProps) {
	return (
		<Modal
			isOpen={isOpen}
			onClose={onClose}
			title={title}
			description={description}
			maxWidthClass="max-w-sm"
		>
			<div className="mt-6 flex items-center justify-end gap-2">
				<Button
					type="button"
					variant="outline"
					size="sm"
					onClick={onClose}
					className="text-xs h-8 px-3 rounded-lg"
				>
					{cancelLabel}
				</Button>

				<Button
					type="button"
					variant={variant}
					size="sm"
					onClick={() => {
						onConfirm();
						onClose();
					}}
					className="text-xs h-8 px-3 rounded-lg"
				>
					{confirmLabel}
				</Button>
			</div>
		</Modal>
	);
}
