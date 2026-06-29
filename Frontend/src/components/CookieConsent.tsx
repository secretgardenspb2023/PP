"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const KEY = "cookie-consent"; // "granted" | "denied"

// Баннер согласия на cookie (ТЗ 8.8 / 152-ФЗ). Аналитика (Яндекс.Метрика)
// включается только после «Принять»; выбор сохраняется и его можно изменить
// ссылкой «Настройки cookie» в подвале (событие cookie-consent-reopen).
export function CookieConsent() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(KEY)) {
      setShow(true);
    }
    const reopen = () => setShow(true);
    window.addEventListener("cookie-consent-reopen", reopen);
    return () => window.removeEventListener("cookie-consent-reopen", reopen);
  }, []);

  function decide(value: "granted" | "denied") {
    localStorage.setItem(KEY, value);
    if (value === "granted") {
      window.dispatchEvent(new Event("cookie-consent-granted"));
    }
    setShow(false);
  }

  if (!show) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-[90] border-t border-line bg-white/95 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur">
      <div className="container-page flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-3xl text-[14px] leading-relaxed text-accent-ink">
          Мы используем файлы cookie и сервис Яндекс.Метрика, чтобы анализировать
          посещаемость и улучшать сайт. Нажимая «Принять», вы соглашаетесь на их
          использование. Подробнее — в{" "}
          <Link href="/privacy" className="font-medium text-brand hover:text-brand-dark">
            Политике использования cookie
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => decide("denied")}
            className="h-10 rounded-control border border-line px-4 text-[14px] font-medium text-ink transition-colors hover:bg-surface"
          >
            Отклонить
          </button>
          <button
            type="button"
            onClick={() => decide("granted")}
            className="h-10 rounded-control bg-brand px-5 text-[14px] font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
          >
            Принять
          </button>
        </div>
      </div>
    </div>
  );
}
