"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { telegramLogin } from "@/lib/auth";
import { useAuth } from "@/components/auth/AuthProvider";

const BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, unknown>) => void;
  }
}

// Telegram Login Widget (ТЗ 3.5). Рендерит официальную кнопку Telegram; после
// подтверждения шлёт подписанные данные на бэкенд и сразу заводит сессию.
// Кнопка появляется, только если задан бот (NEXT_PUBLIC_TELEGRAM_BOT_USERNAME)
// и у бота настроен /setdomain на текущий домен.
export function TelegramLogin() {
  const router = useRouter();
  const { applySession } = useAuth();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = ref.current;
    if (!BOT || !host) return;
    window.onTelegramAuth = async (user) => {
      try {
        const data: Record<string, string> = {};
        for (const [k, v] of Object.entries(user)) data[k] = String(v);
        const { access, user: u } = await telegramLogin(data);
        applySession(access, u);
        router.push("/profile");
      } catch {
        /* пользователь может повторить */
      }
    };
    const s = document.createElement("script");
    s.src = "https://telegram.org/js/telegram-widget.js?22";
    s.async = true;
    s.setAttribute("data-telegram-login", BOT);
    s.setAttribute("data-size", "large");
    s.setAttribute("data-radius", "10");
    s.setAttribute("data-onauth", "onTelegramAuth(user)");
    s.setAttribute("data-request-access", "write");
    host.appendChild(s);
    return () => {
      host.innerHTML = "";
    };
  }, [router, applySession]);

  if (!BOT) return null;
  return <div ref={ref} className="flex justify-center pt-1" />;
}
