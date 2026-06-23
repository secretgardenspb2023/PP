"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { confirmPasswordReset } from "@/lib/auth";

function ResetInner() {
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "busy" | "ok">("idle");
  const [account, setAccount] = useState("");

  const linkValid = Boolean(uid && token);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Пароли не совпадают.");
      return;
    }
    setState("busy");
    try {
      const res = await confirmPasswordReset(uid, token, password);
      setAccount(res.login || res.email || "");
      setState("ok");
      setTimeout(() => router.replace("/login"), 3500);
    } catch (err) {
      setState("idle");
      setError(err instanceof Error ? err.message : "Не удалось изменить пароль.");
    }
  }

  if (!linkValid) {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center">
        <p className="text-[16px] text-ink">
          Ссылка недействительна или устарела. Запросите новую на странице{" "}
          <Link href="/forgot-password" className="font-medium text-brand hover:text-brand-dark">
            восстановления пароля
          </Link>
          .
        </p>
      </div>
    );
  }

  if (state === "ok") {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center">
        <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-brand/15 text-2xl text-brand">
          ✓
        </div>
        <p className="text-[16px] text-ink">
          {account ? (
            <>
              Логин <span className="font-semibold">{account}</span> — пароль успешно изменён.
            </>
          ) : (
            "Пароль успешно изменён."
          )}
        </p>
        <p className="mt-2 text-[14px] text-muted">Перенаправляем ко входу…</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-card border border-line bg-white p-6">
      <p className="text-[15px] text-muted">Придумайте новый пароль для входа.</p>
      {error && (
        <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{error}</p>
      )}
      <label className="block">
        <span className="mb-1 block text-[14px] text-accent-ink">Новый пароль</span>
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
      <label className="block">
        <span className="mb-1 block text-[14px] text-accent-ink">Повторите пароль</span>
        <input
          type="password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="auth-input"
          autoComplete="new-password"
        />
      </label>

      <button
        type="submit"
        disabled={state === "busy" || !password || !confirm}
        className="h-11 w-full rounded-control bg-brand font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
      >
        {state === "busy" ? "Сохраняем…" : "Сменить пароль"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="container-page flex justify-center py-16">
      <div className="w-full max-w-md">
        <h1 className="mb-6 text-center text-[32px] font-bold text-ink">Новый пароль</h1>
        <Suspense fallback={<p className="text-center text-muted">Загрузка…</p>}>
          <ResetInner />
        </Suspense>
      </div>
    </div>
  );
}
