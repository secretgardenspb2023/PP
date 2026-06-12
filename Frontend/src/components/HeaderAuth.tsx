"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/AuthProvider";

export function HeaderAuth() {
  const { user, loading, signOut } = useAuth();

  if (loading) {
    return <div className="ml-auto h-9 w-32 animate-pulse rounded-control bg-surface" />;
  }

  if (user) {
    return (
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <Link
          href="/profile"
          className="max-w-[160px] truncate rounded-control px-4 py-2 text-[16px] font-medium text-brand-dark transition-colors hover:bg-surface"
          title={user.full_name || user.email}
        >
          {user.full_name || user.email}
        </Link>
        <button
          type="button"
          onClick={() => void signOut()}
          className="rounded-control border border-line px-4 py-2 text-[16px] font-medium text-accent-ink transition-colors hover:border-brand hover:text-brand"
        >
          Выход
        </button>
      </div>
    );
  }

  return (
    <div className="ml-auto flex shrink-0 items-center gap-2">
      <Link
        href="/login"
        className="rounded-control px-4 py-2 text-[16px] font-medium text-brand-dark transition-colors hover:bg-surface"
      >
        Вход
      </Link>
      <Link
        href="/register"
        className="rounded-control bg-brand px-4 py-2 text-[16px] font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
      >
        Регистрация
      </Link>
    </div>
  );
}
