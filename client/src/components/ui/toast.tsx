"use client";

import React, { createContext, useCallback, useContext, useState } from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
	id: string;
	message: string;
	type: ToastType;
}

interface ToastContextType {
	toast: {
		success: (message: string) => void;
		error: (message: string) => void;
		info: (message: string) => void;
	};
}

const ToastContext = createContext<ToastContextType | null>(null);

// Global dispatcher to allow calling toast.success() / toast.error() outside React tree or inside components
type ToastListener = (toast: Omit<Toast, "id">) => void;
const listeners = new Set<ToastListener>();

export const toast = {
	success: (message: string) => {
		listeners.forEach((fn) => {
			fn({ message, type: "success" });
		});
	},
	error: (message: string) => {
		listeners.forEach((fn) => {
			fn({ message, type: "error" });
		});
	},
	info: (message: string) => {
		listeners.forEach((fn) => {
			fn({ message, type: "info" });
		});
	},
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
	const [toasts, setToasts] = useState<Toast[]>([]);

	const addToast = useCallback(({ message, type }: Omit<Toast, "id">) => {
		const id = Math.random().toString(36).substring(2, 9);
		setToasts((prev) => [...prev, { id, message, type }]);

		setTimeout(() => {
			setToasts((prev) => prev.filter((t) => t.id !== id));
		}, 4000);
	}, []);

	React.useEffect(() => {
		listeners.add(addToast);
		return () => {
			listeners.delete(addToast);
		};
	}, [addToast]);

	const removeToast = (id: string) => {
		setToasts((prev) => prev.filter((t) => t.id !== id));
	};

	return (
		<ToastContext.Provider value={{ toast }}>
			{children}
			{/* Toast Container */}
			<div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
				{toasts.map((t) => (
					<div
						key={t.id}
						className={`pointer-events-auto flex items-center justify-between gap-3 p-3.5 rounded-xl border text-sm shadow-lg backdrop-blur-md transition-all animate-in fade-in slide-in-from-bottom-3 duration-200 ${
							t.type === "error"
								? "bg-destructive/15 border-destructive/30 text-destructive-foreground dark:text-red-400"
								: t.type === "success"
									? "bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
									: "bg-card border-border text-foreground"
						}`}
					>
						<div className="flex items-center gap-2 font-medium">
							{t.type === "error" && (
								<svg
									className="size-4 shrink-0 text-red-500"
									viewBox="0 0 20 20"
									fill="currentColor"
								>
									<title>Error</title>
									<path
										fillRule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
										clipRule="evenodd"
									/>
								</svg>
							)}
							{t.type === "success" && (
								<svg
									className="size-4 shrink-0 text-emerald-500"
									viewBox="0 0 20 20"
									fill="currentColor"
								>
									<title>Success</title>
									<path
										fillRule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
										clipRule="evenodd"
									/>
								</svg>
							)}
							<span>{t.message}</span>
						</div>
						<button
							type="button"
							onClick={() => removeToast(t.id)}
							className="opacity-70 hover:opacity-100 transition-opacity p-0.5 rounded"
						>
							<svg
								className="size-3.5"
								viewBox="0 0 20 20"
								fill="currentColor"
							>
								<title>Close</title>
								<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
							</svg>
						</button>
					</div>
				))}
			</div>
		</ToastContext.Provider>
	);
}

export function useToast() {
	const context = useContext(ToastContext);
	if (!context) {
		return { toast };
	}
	return context;
}
