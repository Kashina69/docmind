import { AuthGoogleButton } from "./components/AuthGoogleButton";

export default function AuthLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<div className="min-h-screen flex items-center justify-center bg-background px-4">
			<div className="w-full max-w-md">
				{/* Logo */}
				{children}
				<AuthGoogleButton />
			</div>
		</div>
	);
}
