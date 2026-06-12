// Auth API client (stage 3 backend at /api/v1/auth/).
// Access token returned in body; refresh token lives in an HttpOnly cookie
// scoped to /api/v1/auth/ (works same-origin in prod). credentials:"include"
// so the refresh cookie is set/sent.
const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export type User = {
  email: string;
  full_name?: string;
  is_active?: boolean;
  [k: string]: unknown;
};

async function post(path: string, body?: unknown, token?: string) {
  const res = await fetch(`${API}/auth${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail || `Ошибка (${res.status})`);
  return data;
}

export async function login(email: string, password: string): Promise<{ access: string }> {
  return post("/login/", { email, password }) as Promise<{ access: string }>;
}

export async function register(email: string, full_name: string, password: string) {
  return post("/register/", { email, full_name, password });
}

export async function refresh(): Promise<{ access: string }> {
  return post("/token/refresh/") as Promise<{ access: string }>;
}

export async function logout(): Promise<void> {
  await post("/logout/").catch(() => {});
}

export async function verifyEmail(token: string) {
  return post("/verify-email/", { token });
}

export async function me(token: string): Promise<User> {
  const res = await fetch(`${API}/auth/me/`, {
    credentials: "include",
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`me ${res.status}`);
  return res.json();
}

export const googleLoginUrl = `${API}/auth/google/`;
