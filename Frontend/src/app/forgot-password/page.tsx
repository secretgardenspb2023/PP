"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { requestPasswordReset } from "@/lib/auth";
import { SmartCaptcha, type CaptchaHandle } from "@/components/auth/SmartCaptcha";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const captchaRef = useRef<CaptchaHandle>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const captchaToken = (await captchaRef.current?.execute()) ?? "";
      await requestPasswordReset(email, captchaToken);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить письмо");
      setBusy(false);
    }
  }

  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Восстановление пароля</h1>

        {sent ? (
          <div className="rounded-card border border-line bg-white p-8 text-center">
            <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-brand/15 text-2xl text-brand">
              ✓
            </div>
            <p className="text-[16px] text-ink">
              Если такой email зарегистрирован, мы отправили на него письмо со ссылкой для смены
              пароля. Проверьте почту (и папку «Спам»).
            </p>
            <Link
              href="/login"
              className="mt-5 inline-block font-medium text-brand hover:text-brand-dark"
            >
              Вернуться ко входу
            </Link>
          </div>
        ) : (
          <>
            <form onSubmit={onSubmit} className="space-y-4 rounded-card border border-line bg-white p-6">
              <p className="text-[15px] text-muted">
                Введите email, указанный при регистрации. Мы пришлём ссылку для смены пароля.
              </p>
              {error && (
                <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{error}</p>
              )}
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

              <SmartCaptcha ref={captchaRef} />

              <button
                type="submit"
                disabled={busy}
                className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
              >
                {busy ? "Отправляем…" : "Отправить ссылку"}
              </button>
            </form>

            <p className="mt-4 text-center text-[15px] text-muted">
              Вспомнили пароль?{" "}
              <Link href="/login" className="font-medium text-brand hover:text-brand-dark">
                Вход
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
