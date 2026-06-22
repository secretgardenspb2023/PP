"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

// Невидимая Yandex SmartCaptcha. Виджет рендерится скрыто; токен запрашиваем
// императивно методом execute() в момент сабмита формы. Если ключ не задан
// (NEXT_PUBLIC_SMARTCAPTCHA_CLIENT_KEY пуст) — компонент ничего не рисует и
// execute() возвращает пустую строку, т.е. капча просто отключена на клиенте.
const SITEKEY = process.env.NEXT_PUBLIC_SMARTCAPTCHA_CLIENT_KEY;
const SCRIPT_SRC = "https://smartcaptcha.yandexcloud.net/captcha.js";

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

// Грузим скрипт один раз и ждём, пока window.smartCaptcha реально появится
// (после события load API инициализируется не мгновенно — опрашиваем).
function whenReady(): Promise<SmartCaptchaApi> {
  return new Promise((resolve, reject) => {
    if (window.smartCaptcha) return resolve(window.smartCaptcha);
    if (!document.querySelector(`script[src^="${SCRIPT_SRC}"]`)) {
      const s = document.createElement("script");
      s.src = SCRIPT_SRC;
      s.async = true;
      s.defer = true;
      document.head.appendChild(s);
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      if (window.smartCaptcha) {
        window.clearInterval(timer);
        resolve(window.smartCaptcha);
      } else if (Date.now() - started > 12000) {
        window.clearInterval(timer);
        reject(new Error("smartcaptcha: API не загрузилось"));
      }
    }, 100);
  });
}

export const SmartCaptcha = forwardRef<CaptchaHandle>(function SmartCaptcha(_props, ref) {
  const elRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<number | null>(null);
  const executedRef = useRef(false);
  const resolverRef = useRef<((t: string) => void) | null>(null);

  useEffect(() => {
    if (!SITEKEY || !elRef.current) return;
    let cancelled = false;
    whenReady()
      .then((api) => {
        if (cancelled || !elRef.current || widgetIdRef.current !== null) return;
        widgetIdRef.current = api.render(elRef.current, {
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
      .catch((e) => console.warn(e));
    return () => {
      cancelled = true;
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      execute: () =>
        new Promise<string>((resolve) => {
          const api = window.smartCaptcha;
          if (!SITEKEY || widgetIdRef.current === null || !api) return resolve("");
          resolverRef.current = resolve;
          if (executedRef.current) api.reset(widgetIdRef.current); // повторный сабмит → свежий токен
          executedRef.current = true;
          api.execute(widgetIdRef.current);
        }),
    }),
    [],
  );

  if (!SITEKEY) return null;
  return <div ref={elRef} />;
});
