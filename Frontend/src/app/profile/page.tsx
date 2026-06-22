"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

export default function ProfilePage() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="container-page py-16 text-center text-muted">Загрузка…</div>
    );
  }

  // Соц-аккаунты без реального email получают «технический» адрес
  // VK-…@social.poiskplant.ru — его не показываем, вместо него «Вход через …».
  const PROVIDER_LABEL: Record<string, string> = {
    VK: "ВКонтакте",
    TG: "Telegram",
    "Гугл": "Google",
  };
  const isSocialEmail = String(user.email).endsWith("@social.poiskplant.ru");
  const loginVia = PROVIDER_LABEL[String(user.social_provider ?? "")] ?? "соцсеть";

  return (
    <div className="container-page py-12">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-[32px] font-bold text-ink">Личный кабинет</h1>

        <div className="flex items-center gap-4 rounded-card border border-line bg-white p-6">
          {user.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={String(user.avatar_url)}
              alt={user.full_name || "Аватар"}
              className="size-16 shrink-0 rounded-full object-cover"
            />
          ) : (
            <div className="grid size-16 shrink-0 place-items-center rounded-full bg-brand/15 text-2xl font-bold text-brand">
              {(user.full_name || user.email).charAt(0).toUpperCase()}
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate text-[20px] font-semibold text-ink">
              {user.full_name || "Пользователь"}
            </p>
            <p className="truncate text-[15px] text-muted">
              {isSocialEmail ? `Вход через ${loginVia}` : user.email}
            </p>
          </div>
        </div>

        <dl className="mt-4 rounded-card border border-line bg-white p-6 text-[15px]">
          <div className="flex justify-between border-b border-line py-2">
            <dt className="text-muted">{isSocialEmail ? "Вход через" : "Email"}</dt>
            <dd className="font-medium text-ink">{isSocialEmail ? loginVia : user.email}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted">Статус</dt>
            <dd className="font-medium text-brand-dark">
              {user.is_active === false ? "не подтверждён" : "активен"}
            </dd>
          </div>
        </dl>

        <button
          type="button"
          onClick={() => {
            void signOut();
            router.push("/");
          }}
          className="mt-6 rounded-control border border-line px-5 py-2.5 font-medium text-accent-ink transition-colors hover:border-danger hover:text-danger"
        >
          Выйти из аккаунта
        </button>
      </div>
    </div>
  );
}
