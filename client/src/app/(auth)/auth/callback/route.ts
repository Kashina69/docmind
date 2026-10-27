import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
	const { searchParams, origin } = new URL(request.url);
	const code = searchParams.get("code");

	if (code) {
		const redirectTo = NextResponse.redirect(`${origin}/dashboard`);

		const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
		const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

		const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
			cookies: {
				getAll() {
					return request.cookies.getAll();
				},
				setAll(cookiesToSet) {
					cookiesToSet.forEach(({ name, value, options }) => {
						redirectTo.cookies.set(name, value, options);
					});
				},
			},
		});

		const { error } = await supabase.auth.exchangeCodeForSession(code);
		if (!error) {
			return redirectTo;
		}
	}

	return NextResponse.redirect(`${origin}/login?error=auth_failed`);
}
