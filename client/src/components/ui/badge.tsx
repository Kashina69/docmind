import type React from "react";

export type BadgeStatus = "processed" | "processing" | "failed" | string;

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
	status?: BadgeStatus;
	label?: string;
	dot?: boolean;
}

const statusConfig: Record<
	string,
	{ label: string; className: string; dotColor: string }
> = {
	processed: {
		label: "Processed",
		className: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
		dotColor: "bg-emerald-400",
	},
	processing: {
		label: "Processing",
		className: "text-amber-500 bg-amber-500/10 border-amber-500/20",
		dotColor: "bg-amber-400 animate-pulse",
	},
	failed: {
		label: "Failed",
		className: "text-rose-500 bg-rose-500/10 border-rose-500/20",
		dotColor: "bg-rose-400",
	},
};

export function Badge({
	status = "processing",
	label,
	dot = true,
	className = "",
	children,
	...props
}: BadgeProps) {
	const config = statusConfig[status] || {
		label: status,
		className: "text-muted-foreground bg-muted border-border",
		dotColor: "bg-muted-foreground",
	};

	const displayText = label || children || config.label;

	return (
		<span
			className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] font-medium leading-none ${config.className} ${className}`}
			{...props}
		>
			{dot && (
				<span className={`size-1.5 rounded-full ${config.dotColor}`} />
			)}
			{displayText}
		</span>
	);
}

// Aliased as Pill as well
export { Badge as Pill };
