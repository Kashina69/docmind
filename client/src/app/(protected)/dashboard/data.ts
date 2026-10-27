export interface DocumentItem {
	id: string;
	name: string;
	type: string;
	date: string;
	status: "processed" | "processing" | "failed";
	thumbnail?: string;
}

export const initialDocuments: DocumentItem[] = [
	{
		id: "doc-1",
		name: "Quarterly_Financial_Report_Q3.pdf",
		type: "PDF",
		date: "Oct 04, 2026",
		status: "processed",
	},
	{
		id: "doc-2",
		name: "System_Architecture_Overview.docx",
		type: "DOCX",
		date: "Oct 05, 2026",
		status: "processing",
	},
	{
		id: "doc-3",
		name: "Product_Requirements_Spec.pdf",
		type: "PDF",
		date: "Oct 06, 2026",
		status: "processing",
	},
	{
		id: "doc-4",
		name: "Legacy_API_Documentation.txt",
		type: "TXT",
		date: "Oct 07, 2026",
		status: "failed",
	},
];
