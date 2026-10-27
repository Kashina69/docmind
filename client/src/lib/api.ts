import { getAccessToken } from "./supabase";

interface FetchOptions extends RequestInit {
	params?: Record<string, string | number | boolean | undefined>;
}

export async function api<T = unknown>(
	endpoint: string,
	options: FetchOptions = {},
): Promise<T> {
	const { params, headers, ...rest } = options;

	let url = endpoint;
	if (params) {
		const searchParams = new URLSearchParams();
		Object.entries(params).forEach(([key, val]) => {
			if (val !== undefined) searchParams.append(key, String(val));
		});
		const queryString = searchParams.toString();
		if (queryString) {
			url += (url.includes("?") ? "&" : "?") + queryString;
		}
	}

	const token = await getAccessToken();

	const res = await fetch(url, {
		...rest,
		headers: {
			"Content-Type": "application/json",
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...headers,
		},
	});

	if (!res.ok) {
		const errorText = await res.text().catch(() => "Unknown error");
		throw new Error(`API error ${res.status}: ${errorText}`);
	}

	// Handle empty responses (like 204 No Content)
	const contentType = res.headers.get("content-type");
	if (contentType?.includes("application/json")) {
		return res.json();
	}

	return (await res.text()) as unknown as T;
}

export default api;
