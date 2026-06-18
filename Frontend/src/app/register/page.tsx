"use client";

import Link from "next/link";
import { useState } from "react";
import { register } from "@/lib/auth";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(email, fullName, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось зарегистрироваться");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Регистрация</h1>

        {done ? (
          <div className="rounded-card border border-line bg-white p-6 text-center">
            <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-brand/15 text-2xl text-brand">
              ✓
            </div>
            <p className="text-[16px] text-ink">Письмо отправлено на {email}.</p>
            <p className="mt-1 text-[15px] text-muted">
              Перейдите по ссылке из письма, чтобы подтвердить адрес и активировать аккаунт.
            </p>
            <Link
              href="/login"
              className="mt-5 inline-block rounded-control bg-brand px-5 py-2.5 font-medium text-white hover:bg-brand-light hover:text-brand-dark"
            >
              Перейти ко входу
            </Link>
          </div>
        ) : (
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

            <button
              type="submit"
              disabled={busy}
              className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
            >
              {busy ? "Регистрация…" : "Зарегистрироваться"}
            </button>
          </form>
        )}

        {!done && (
          <p className="mt-4 text-center text-[15px] text-muted">
            Уже есть аккаунт?{" "}
            <Link href="/login" className="font-medium text-brand hover:text-brand-dark">
              Вход
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
