"use client";

import { useEffect, useRef } from "react";

const BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;

// Telegram Login Widget в redirect-режиме (data-auth-url): после подтверждения
// Telegram сам перенаправляет браузер на наш бэкенд-callback с подписанными
// данными — надёжнее JS-колбэка в SPA. Дальше как Google/VK: бэкенд ставит
// refresh-cookie и возвращает на /auth/callback, где AuthProvider поднимает сессию.
// Кнопка появляется, только если задан бот и у него /setdomain на текущий домен.
export function TelegramLogin() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = ref.current;
    if (!BOT || !host) return;
    host.innerHTML = "";
    const s = document.createElement("script");
    s.src = "https://telegram.org/js/telegram-widget.js?22";
    s.async = true;
    s.setAttribute("data-telegram-login", BOT);
    s.setAttribute("data-size", "large");
    s.setAttribute("data-radius", "10");
    s.setAttribute("data-auth-url", `${window.location.origin}/api/v1/auth/telegram/callback/`);
    s.setAttribute("data-request-access", "write");
    host.appendChild(s);
    return () => {
      host.innerHTML = "";
    };
  }, []);

  if (!BOT) return null;
  return <div ref={ref} className="flex justify-center pt-1" />;
}
