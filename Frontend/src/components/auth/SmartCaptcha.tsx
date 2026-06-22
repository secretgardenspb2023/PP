"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

// Невидимая Yandex SmartCaptcha. Виджет рендерится скрыто; токен запрашиваем
// императивно методом execute() в момент сабмита формы. Если ключ не задан
// (NEXT_PUBLIC_SMARTCAPTCHA_CLIENT_KEY пуст) — компонент ничего не рисует и
// execute() возвращает пустую строку, т.е. капча просто отключена на клиенте.
const SITEKEY = process.env.NEXT_PUBLIC_SMARTCAPTCHA_CLIENT_KEY;
const SCRIPT_SRC = "https://smartcaptcha.yandexcloud.net/captcha.js?render=onload";

type SmartCaptchaApi = {
  render: (el: HTMLElement, opts: Record<string, unknown>) => number;
  execute: (id?: number) => void;
  reset: (id?: number) => void;
};

declare global {
  interface Window {
    smartCaptcha?: SmartCaptchaApi;
  }
}

export type CaptchaHandle = { execute: () => Promise<string> };

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.smartCaptcha) return resolve();
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src^="https://smartcaptcha.yandexcloud.net/captcha.js"]',
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("captcha")));
      return;
    }
    const s = document.createElement("script");
    s.src = SCRIPT_SRC;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("captcha"));
    document.head.appendChild(s);
  });
}

export const SmartCaptcha = forwardRef<CaptchaHandle>(function SmartCaptcha(_props, ref) {
  const elRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<number | null>(null);
  const resolverRef = useRef<((t: string) => void) | null>(null);

  useEffect(() => {
    if (!SITEKEY || !elRef.current) return;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !window.smartCaptcha || !elRef.current || widgetIdRef.current !== null) return;
        widgetIdRef.current = window.smartCaptcha.render(elRef.current, {
          sitekey: SITEKEY,
          invisible: true,
          hideShield: true,
          hl: "ru",
          callback: (token: string) => {
            resolverRef.current?.(token);
            resolverRef.current = null;
          },
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      execute: () =>
        new Promise<string>((resolve) => {
          if (!SITEKEY || widgetIdRef.current === null || !window.smartCaptcha) return resolve("");
          resolverRef.current = resolve;
          window.smartCaptcha.reset(widgetIdRef.current);
          window.smartCaptcha.execute(widgetIdRef.current);
        }),
    }),
    [],
  );

  if (!SITEKEY) return null;
  return <div ref={elRef} />;
});
