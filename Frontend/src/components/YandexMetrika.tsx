"use client";

import Script from "next/script";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

// Номер счётчика можно переопределить через env, по умолчанию — боевой.
const YM_ID = process.env.NEXT_PUBLIC_YM_ID || "87721057";

declare global {
  interface Window {
    ym?: (...args: unknown[]) => void;
  }
}

// SPA-переходы (Next.js меняет URL без перезагрузки) — шлём 'hit' вручную.
// Первый заход уже учитывает init в скрипте ниже, поэтому его пропускаем.
function MetrikaTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (typeof window.ym === "function") {
      const qs = searchParams?.toString();
      window.ym(Number(YM_ID), "hit", pathname + (qs ? `?${qs}` : ""));
    }
  }, [pathname, searchParams]);

  return null;
}

// Информационная модель согласия (стандарт рунета): Метрика грузится сразу,
// кроме случая явного «Отклонить» (cookie-consent=denied). Это даёт корректную
// «Проверку счётчика» у Яндекса и учёт всех визитов; отказ — отключает аналитику.
export function YandexMetrika() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("cookie-consent") !== "denied") {
      setEnabled(true);
    }
    const grant = () => setEnabled(true);
    const deny = () => setEnabled(false);
    window.addEventListener("cookie-consent-granted", grant);
    window.addEventListener("cookie-consent-denied", deny);
    return () => {
      window.removeEventListener("cookie-consent-granted", grant);
      window.removeEventListener("cookie-consent-denied", deny);
    };
  }, []);

  if (!enabled) return null;

  return (
    <>
      <Script id="yandex-metrika" strategy="afterInteractive">
        {`(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();for(var j=0;j<e.scripts.length;j++){if(e.scripts[j].src===r){return;}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');ym(${YM_ID},'init',{webvisor:true,clickmap:true,accurateTrackBounce:true,trackLinks:true});`}
      </Script>
      <Suspense fallback={null}>
        <MetrikaTracker />
      </Suspense>
    </>
  );
}
