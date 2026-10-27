"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function ProtectedLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	const router = useRouter();
	const [authenticated, setAuthenticated] = useState<boolean | null>(null);

	useEffect(() => {
		supabase.auth.getUser().then(({ data: { user } }) => {
			if (!user) {
				router.replace("/login");
			} else {
				setAuthenticated(true);
			}
		});

		const {
			data: { subscription },
		} = supabase.auth.onAuthStateChange((_event, session) => {
			if (!session) {
				router.replace("/login");
			} else {
				setAuthenticated(true);
			}
		});

		return () => {
			subscription.unsubscribe();
		};
	}, [router]);

	if (authenticated === null) {
		return (
			<div className="flex h-screen items-center justify-center bg-background text-muted-foreground text-sm">
				Loading...
			</div>
		);
	}

	return <>{children}</>;
}
