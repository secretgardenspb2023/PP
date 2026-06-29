"use client";

// Ссылка в подвале для повторного открытия баннера cookie (смена решения).
export function CookieSettingsLink() {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("cookie-consent-reopen"))}
      className="text-left hover:text-brand"
    >
      Настройки cookie
    </button>
  );
}
