"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { register } from "@/lib/auth";
import { SmartCaptcha, type CaptchaHandle } from "@/components/auth/SmartCaptcha";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const captchaRef = useRef<CaptchaHandle>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const captchaToken = (await captchaRef.current?.execute()) ?? "";
      await register(email, fullName, password, captchaToken);
      // Письмо с кодом ушло — отправляем пользователя на экран ввода кода.
      router.push(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось зарегистрироваться");
      setBusy(false);
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Регистрация</h1>

        <form onSubmit={onSubmit} className="space-y-4 rounded-card border border-line bg-white p-6">
          {error && (
            <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{error}</p>
          )}
          <label className="block">
            <span className="mb-1 block text-[14px] text-accent-ink">Имя</span>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="auth-input"
              autoComplete="name"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[14px] text-accent-ink">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="auth-input"
              autoComplete="email"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[14px] text-accent-ink">Пароль</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              autoComplete="new-password"
            />
            <span className="mt-1 block text-[13px] text-muted">
              Минимум 8 символов, не только цифры и не слишком простой.
            </span>
          </label>

          <SmartCaptcha ref={captchaRef} />

          <button
            type="submit"
            disabled={busy}
            className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
          >
            {busy ? "Регистрация…" : "Зарегистрироваться"}
          </button>
        </form>

        <p className="mt-4 text-center text-[15px] text-muted">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="font-medium text-brand hover:text-brand-dark">
            Вход
          </Link>
        </p>
      </div>
    </div>
  );
}
