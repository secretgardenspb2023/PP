"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

function CallbackInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const error = sp.get("error");

  // The backend set the refresh cookie before redirecting here; AuthProvider
  // restores the session on mount. Once we have the user → возвращаем на страницу,
  // с которой начинали вход (сохранена в sessionStorage перед соц-входом).
  useEffect(() => {
    if (!error && !loading && user) {
      let dest = "/";
      try {
        dest = sessionStorage.getItem("auth_next") || "/";
        sessionStorage.removeItem("auth_next");
      } catch {
        /* sessionStorage недоступен — уходим на главную */
      }
      router.replace(dest);
    }
  }, [error, loading, user, router]);

  if (error) {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center shadow-soft">
        <p className="text-[16px] text-danger">Вход через соцсеть отменён или не удался.</p>
        <Link href="/login" className="mt-4 inline-block font-medium text-brand hover:text-brand-dark">
          Вернуться ко входу
        </Link>
      </div>
    );
  }

  if (!loading && !user) {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center shadow-soft">
        <p className="text-[16px] text-danger">Не удалось завершить вход. Попробуйте ещё раз.</p>
        <Link href="/login" className="mt-4 inline-block font-medium text-brand hover:text-brand-dark">
          Ко входу
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 py-8 text-center text-muted">
      <span className="size-8 animate-spin rounded-full border-2 border-line border-t-brand" />
      Завершаем вход…
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <div className="container-page flex justify-center py-20">
      <div className="w-full max-w-md">
        <Suspense fallback={<p className="text-center text-muted">Загрузка…</p>}>
          <CallbackInner />
        </Suspense>
      </div>
    </div>
  );
}
