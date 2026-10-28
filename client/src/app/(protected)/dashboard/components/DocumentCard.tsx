import { FileText } from "@/components/icons";
import { Pill } from "@/components/ui";
import type { DocumentItem } from "../data";

interface DocumentCardProps {
	document: DocumentItem;
	date?: string;
}

export function DocumentCard({ document, date }: DocumentCardProps) {
	return (
		<div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between hover:border-border/80 transition-colors">
			<div className="flex items-start gap-3">
				<div className="relative size-12 rounded-xl bg-muted/60 border border-border/50 flex items-center justify-center shrink-0 text-muted-foreground overflow-hidden">
					<FileText className="size-6 text-foreground/70" />
				</div>

				<div className="flex-1 min-w-0">
					<p
						className="text-sm font-medium text-foreground truncate"
						title={document.filename}
					>
						{document.filename}
					</p>
					<span className="inline-block mt-0.5 text-xs text-muted-foreground uppercase font-mono">
						PDF
					</span>
				</div>
			</div>

			<div className="mt-4 pt-3 border-t border-border/40 flex items-center justify-between">
				<span className="text-xs text-muted-foreground">{date}</span>
				<Pill status={document.status} />
			</div>
		</div>
	);
}
