interface DocumentStatusBannerProps {
	totalCount: number;
	processingCount: number;
	failedCount?: number;
}

export function DocumentStatusBanner({
	totalCount,
	processingCount,
	failedCount = 0,
}: DocumentStatusBannerProps) {
	let message = "No documents uploaded yet.";

	if (totalCount > 0) {
		if (processingCount === 0 && failedCount === 0) {
			message = "All your documents are processed.";
		} else if (processingCount === totalCount) {
			message = "Your documents are still processing...";
		} else if (processingCount > 0) {
			message = `${processingCount} ${
				processingCount === 1 ? "document is" : "documents are"
			} still getting processed.`;
		} else if (failedCount > 0) {
			message = `All processing finished (${failedCount} failed).`;
		}
	}

	return (
		<div className="text-sm text-muted-foreground bg-muted/30 border border-border/50 rounded-xl px-4 py-2.5">
			{message}
		</div>
	);
}
