"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { resendCode, verifyEmail } from "@/lib/auth";
import { useAuth } from "@/components/auth/AuthProvider";

function VerifyInner() {
  const emailFromLink = useSearchParams().get("email") ?? "";
  const router = useRouter();
  const { applySession } = useAuth();
  const [email, setEmail] = useState(emailFromLink);
  const [code, setCode] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "ok" | "err">("idle");
  const [msg, setMsg] = useState("");
  const [resent, setResent] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setState("busy");
    setMsg("");
    try {
      const { access, user } = await verifyEmail(email, code.trim());
      // Email подтверждён — бэкенд уже выставил refresh-cookie и вернул токен.
      // Заводим сессию и сразу ведём в личный кабинет, без повторного входа.
      applySession(access, user);
      setState("ok");
      router.replace("/profile");
    } catch (err) {
      setState("err");
      setMsg(err instanceof Error ? err.message : "Не удалось подтвердить email.");
    }
  }

  async function onResend() {
    setResent(false);
    setMsg("");
    try {
      await resendCode(email);
      setResent(true);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Не удалось отправить код.");
    }
  }

  if (state === "ok") {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center">
        <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-brand/15 text-2xl text-brand">
          ✓
        </div>
        <p className="text-[16px] text-ink">Email подтверждён. Входим в аккаунт…</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-card border border-line bg-white p-6">
      <p className="text-[15px] text-muted">
        Мы отправили 6-значный код на вашу почту. Введите его ниже, чтобы активировать аккаунт.
      </p>
      {state === "err" && (
        <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{msg}</p>
      )}
      {resent && (
        <p className="rounded-control bg-brand/10 px-4 py-2 text-[14px] text-brand-dark">
          Новый код отправлен на почту.
        </p>
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
      <label className="block">
        <span className="mb-1 block text-[14px] text-accent-ink">Код из письма</span>
        <input
          type="text"
          required
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          className="auth-input text-center text-[20px] tracking-[0.4em]"
          placeholder="______"
        />
      </label>

      <button
        type="submit"
        disabled={state === "busy" || code.length < 6 || !email}
        className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
      >
        {state === "busy" ? "Проверяем…" : "Подтвердить"}
      </button>

      <p className="text-center text-[14px] text-muted">
        Не пришёл код?{" "}
        <button
          type="button"
          onClick={onResend}
          className="font-medium text-brand hover:text-brand-dark"
        >
          Отправить заново
        </button>
      </p>
    </form>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Подтверждение email</h1>
        <Suspense fallback={<p className="text-center text-muted">Загрузка…</p>}>
          <VerifyInner />
        </Suspense>
      </div>
    </div>
  );
}
