import type { DocumentItem } from "./data";

export const statusStyles: Record<
	DocumentItem["status"],
	{ label: string; badgeClass: string }
> = {
	processed: {
		label: "Processed",
		badgeClass: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
	},
	processing: {
		label: "Processing",
		badgeClass:
			"text-amber-500 bg-amber-500/10 border-amber-500/20 animate-pulse",
	},
	failed: {
		label: "Failed",
		badgeClass: "text-rose-500 bg-rose-500/10 border-rose-500/20",
	},
};
