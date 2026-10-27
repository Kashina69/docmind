import { FileText } from "@/components/icons";
import { Pill } from "@/components/ui";
import type { DocumentItem } from "../data";

interface DocumentListProps {
	documents: DocumentItem[];
	title?: string;
	maxHeightClass?: string;
}

export function DocumentList({
	documents,
	title = "Your Documents",
	maxHeightClass = "max-h-56",
}: DocumentListProps) {
	return (
		<div className="space-y-2.5">
			<div className="flex items-center justify-between text-xs text-muted-foreground">
				<div className="flex items-center gap-1.5 font-medium text-foreground">
					<FileText className="size-4" />
					<span>{title}</span>
				</div>
				<span>{documents.length} files</span>
			</div>

			<div className={`space-y-2 overflow-y-auto pr-1 ${maxHeightClass}`}>
				{documents.length === 0 ? (
					<p className="text-xs text-muted-foreground text-center py-4">
						No documents uploaded yet.
					</p>
				) : (
					documents.map((doc) => (
						<div
							key={doc.id}
							className="flex items-center justify-between rounded-xl border border-border bg-card p-3 transition-colors"
						>
							<div className="flex items-center gap-3 min-w-0">
								<div className="size-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center shrink-0">
									<span className="text-[10px] font-bold text-rose-500 uppercase">
										{doc.type}
									</span>
								</div>

								<div className="min-w-0">
									<p className="text-xs font-medium text-foreground truncate max-w-[240px] sm:max-w-[320px]">
										{doc.name}
									</p>
									<p className="text-[10px] text-muted-foreground mt-0.5">
										{doc.date}
									</p>
								</div>
							</div>

							{/* Reusable Pill / Badge component */}
							<Pill status={doc.status} />
						</div>
					))
				)}
			</div>
		</div>
	);
}
