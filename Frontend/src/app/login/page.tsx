"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { TelegramLogin } from "@/components/auth/TelegramLogin";
import { SmartCaptcha, type CaptchaHandle } from "@/components/auth/SmartCaptcha";
import { googleLoginUrl, vkLoginUrl } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Капчу показываем только после неудачной попытки (бэкенд возвращает
  // captcha_required) — на первом входе её нет.
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const captchaRef = useRef<CaptchaHandle>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const captchaToken = captchaRequired ? ((await captchaRef.current?.execute()) ?? "") : undefined;
      await signIn(email, password, captchaToken);
      router.push("/profile");
    } catch (err) {
      const data = (err as { data?: { captcha_required?: boolean } }).data;
      if (data?.captcha_required) setCaptchaRequired(true);
      setError(err instanceof Error ? err.message : "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Вход</h1>

        <form onSubmit={onSubmit} className="space-y-4 rounded-card border border-line bg-white p-6">
          {error && (
            <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{error}</p>
          )}
          <Field label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="auth-input"
              autoComplete="email"
            />
          </Field>
          <Field label="Пароль">
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              autoComplete="current-password"
            />
          </Field>

          <div className="-mt-2 text-right">
            <Link
              href="/forgot-password"
              className="text-[13px] text-muted transition-colors hover:text-brand"
            >
              Забыли пароль?
            </Link>
          </div>

          {captchaRequired && <SmartCaptcha ref={captchaRef} />}

          <button
            type="submit"
            disabled={busy}
            className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
          >
            {busy ? "Вход…" : "Войти"}
          </button>

          <div className="relative py-1 text-center text-[13px] text-muted">
            <span className="relative z-10 bg-white px-3">или</span>
            <span className="absolute inset-x-0 top-1/2 border-t border-line" />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <a
              href={googleLoginUrl}
              className="flex h-11 items-center justify-center gap-2 rounded-control border border-line font-medium text-ink transition-colors hover:border-brand"
            >
              Google
            </a>
            <a
              href={vkLoginUrl}
              className="flex h-11 items-center justify-center gap-2 rounded-control border border-line font-medium text-ink transition-colors hover:border-brand"
            >
              ВКонтакте
            </a>
          </div>

          <TelegramLogin />
        </form>

        <p className="mt-4 text-center text-[15px] text-muted">
          Нет аккаунта?{" "}
          <Link href="/register" className="font-medium text-brand hover:text-brand-dark">
            Регистрация
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[14px] text-accent-ink">{label}</span>
      {children}
    </label>
  );
}
