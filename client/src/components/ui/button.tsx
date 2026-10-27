import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ComponentProps<"button"> {
	variant?:
		| "default"
		| "outline"
		| "secondary"
		| "ghost"
		| "destructive"
		| "link";
	size?: "default" | "sm" | "lg" | "icon";
}

const variants: Record<string, string> = {
	default: "bg-primary text-primary-foreground hover:bg-primary/90",
	outline:
		"border border-border bg-background hover:bg-muted text-foreground",
	secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
	ghost: "hover:bg-muted text-foreground",
	destructive:
		"bg-destructive text-destructive-foreground hover:bg-destructive/90",
	link: "text-primary underline-offset-4 hover:underline",
};

const sizes: Record<string, string> = {
	default: "h-9 px-4 py-2 text-sm",
	sm: "h-8 px-3 text-xs",
	lg: "h-10 px-6 text-base",
	icon: "h-9 w-9",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	({ className, variant = "default", size = "default", ...props }, ref) => {
		return (
			<button
				ref={ref}
				className={cn(
					"inline-flex items-center justify-center font-medium rounded-xl transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
					variants[variant] || variants.default,
					sizes[size] || sizes.default,
					className,
				)}
				{...props}
			/>
		);
	},
);
Button.displayName = "Button";
