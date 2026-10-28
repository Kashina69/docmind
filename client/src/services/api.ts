import { getAccessToken } from "@/lib/supabase";

export const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
	"http://localhost:8000";

interface BackendOptions extends RequestInit {
	params?: Record<string, string | number | boolean | undefined>;
}

export async function backendFetch<T>(
	path: string,
	options: BackendOptions = {},
): Promise<T> {
	const { params, headers, ...rest } = options;

	let url = `${API_BASE_URL}${path}`;
	if (params) {
		const search = new URLSearchParams();
		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined) search.append(key, String(value));
		});
		const queryString = search.toString();
		if (queryString) {
			url += (url.includes("?") ? "&" : "?") + queryString;
		}
	}

	const token = await getAccessToken();
	const isForm =
		typeof FormData !== "undefined" && rest.body instanceof FormData;

	const res = await fetch(url, {
		...rest,
		headers: {
			...(isForm ? {} : { "Content-Type": "application/json" }),
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...((headers as Record<string, string>) ?? {}),
		},
	});

	if (!res.ok) {
		const errorText = await res.text().catch(() => "Unknown error");
		throw new Error(`API error ${res.status}: ${errorText}`);
	}

	const contentType = res.headers.get("content-type");
	if (contentType?.includes("application/json")) {
		return res.json() as Promise<T>;
	}

	return (await res.text()) as unknown as T;
}
