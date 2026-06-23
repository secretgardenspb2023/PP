// Auth API client (stage 3 backend at /api/v1/auth/).
// Access token returned in body; refresh token lives in an HttpOnly cookie
// scoped to /api/v1/auth/ (works same-origin in prod). credentials:"include"
// so the refresh cookie is set/sent.
const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export type User = {
  email: string;
  full_name?: string;
  is_active?: boolean;
  avatar_url?: string | null;
  social_provider?: string | null;
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
  if (!res.ok) {
    // Прокидываем разобранное тело в ошибку, чтобы вызывающий код мог прочитать
    // флаги вроде captcha_required (а не только текст сообщения).
    const err = new Error(errorMessage(data, res.status)) as Error & { data?: unknown };
    err.data = data;
    throw err;
  }
  return data;
}

// DRF errors come either as {detail: "..."} or as field errors
// {password: ["…"], email: ["…"]}. Surface them so the user sees the real reason
// (e.g. почему пароль не принят), а не безликое «Ошибка (400)».
function errorMessage(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    const parts: string[] = [];
    for (const v of Object.values(d)) {
      if (Array.isArray(v)) parts.push(...v.map((x) => String(x)));
      else if (typeof v === "string") parts.push(v);
    }
    if (parts.length) return parts.join(" ");
  }
  return `Ошибка (${status})`;
}

export async function login(
  email: string,
  password: string,
  captchaToken?: string,
): Promise<{ access: string }> {
  return post("/login/", { email, password, captcha_token: captchaToken }) as Promise<{ access: string }>;
}

export async function register(
  email: string,
  full_name: string,
  password: string,
  captchaToken?: string,
) {
  return post("/register/", { email, full_name, password, captcha_token: captchaToken });
}

// Шаг 1: запросить письмо со ссылкой на сброс (требует капчу). Бэкенд всегда
// отвечает 200 и не раскрывает, зарегистрирован ли email.
export async function requestPasswordReset(email: string, captchaToken?: string) {
  return post("/password/reset/", { email, captcha_token: captchaToken });
}

// Шаг 2: задать новый пароль по uid+token из ссылки в письме.
export async function confirmPasswordReset(uid: string, token: string, newPassword: string) {
  return post("/password/reset/confirm/", { uid, token, new_password: newPassword });
}

export async function refresh(): Promise<{ access: string }> {
  return post("/token/refresh/") as Promise<{ access: string }>;
}

export async function logout(): Promise<void> {
  await post("/logout/").catch(() => {});
}

export async function verifyEmail(
  email: string,
  code: string,
): Promise<{ access: string; user: User; detail?: string }> {
  return post("/verify-email/", { email, code }) as Promise<{
    access: string;
    user: User;
    detail?: string;
  }>;
}

export async function resendCode(email: string) {
  return post("/verify-email/resend/", { email });
}

export async function me(token: string): Promise<User> {
  const res = await fetch(`${API}/auth/me/`, {
    credentials: "include",
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`me ${res.status}`);
  return res.json();
}

// Telegram Login Widget posts its signed payload here; backend checks the HMAC
// and returns tokens like a normal login.
export async function telegramLogin(
  data: Record<string, string>,
): Promise<{ access: string; user: User }> {
  return post("/telegram/", data) as Promise<{ access: string; user: User }>;
}

export const googleLoginUrl = `${API}/auth/google/`;
export const vkLoginUrl = `${API}/auth/vk/`;
