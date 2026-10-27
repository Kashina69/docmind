import Image from "next/image";
import { FileText } from "@/components/icons";
import { Pill } from "@/components/ui";
import type { DocumentItem } from "../data";

interface DocumentCardProps {
	document: DocumentItem;
}

export function DocumentCard({ document }: DocumentCardProps) {
	return (
		<div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between hover:border-border/80 transition-colors">
			<div className="flex items-start gap-3">
				{/* Document image / thumbnail */}
				<div className="relative size-12 rounded-xl bg-muted/60 border border-border/50 flex items-center justify-center shrink-0 text-muted-foreground overflow-hidden">
					{document.thumbnail ? (
						<Image
							src={document.thumbnail}
							alt={document.name}
							fill
							unoptimized
							className="object-cover rounded-xl"
						/>
					) : (
						<FileText className="size-6 text-foreground/70" />
					)}
				</div>

				{/* File name & type */}
				<div className="flex-1 min-w-0">
					<p
						className="text-sm font-medium text-foreground truncate"
						title={document.name}
					>
						{document.name}
					</p>
					<span className="inline-block mt-0.5 text-xs text-muted-foreground uppercase font-mono">
						{document.type}
					</span>
				</div>
			</div>

			{/* Bottom right: upload date and status */}
			<div className="mt-4 pt-3 border-t border-border/40 flex items-center justify-between">
				<span className="text-xs text-muted-foreground">
					{document.date}
				</span>
				<Pill status={document.status} />
			</div>
		</div>
	);
}
