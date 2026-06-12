"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { verifyEmail } from "@/lib/auth";

function VerifyInner() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<"pending" | "ok" | "err">("pending");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!token) {
      setState("err");
      setMsg("В ссылке нет токена подтверждения.");
      return;
    }
    verifyEmail(token)
      .then(() => setState("ok"))
      .catch((e) => {
        setState("err");
        setMsg(e instanceof Error ? e.message : "Не удалось подтвердить email.");
      });
  }, [token]);

  return (
    <div className="rounded-card border border-line bg-white p-8 text-center">
      {state === "pending" && <p className="text-muted">Подтверждаем email…</p>}
      {state === "ok" && (
        <>
          <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-brand/15 text-2xl text-brand">
            ✓
          </div>
          <p className="text-[16px] text-ink">Email подтверждён. Аккаунт активирован.</p>
          <Link
            href="/login"
            className="mt-5 inline-block rounded-control bg-brand px-5 py-2.5 font-medium text-white hover:bg-brand-light hover:text-brand-dark"
          >
            Войти
          </Link>
        </>
      )}
      {state === "err" && (
        <>
          <p className="text-[16px] text-danger">{msg}</p>
          <Link href="/register" className="mt-4 inline-block font-medium text-brand hover:text-brand-dark">
            Зарегистрироваться заново
          </Link>
        </>
      )}
    </div>
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
