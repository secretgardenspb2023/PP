import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Политика использования файлов cookie — PoiskPlant",
  description:
    "Какие файлы cookie использует PoiskPlant, с какими целями и как управлять согласием.",
};

export default function PrivacyPage() {
  return (
    <div className="container-page max-w-3xl py-10">
      <article className="space-y-6 text-[16px] leading-relaxed text-accent-ink">
        <header>
          <h1 className="text-[32px] font-bold leading-tight text-ink">
            Политика использования файлов cookie
          </h1>
          <p className="mt-2 text-[14px] text-muted">
            Документ описывает, какие файлы cookie использует сайт PoiskPlant
            (poiskplant.ru), с какими целями и как вы можете управлять своим согласием.
          </p>
        </header>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">1. Что такое файлы cookie</h2>
          <p>
            Файлы cookie — это небольшие текстовые файлы, которые сохраняются в вашем
            браузере при посещении сайта. Они позволяют сайту запоминать ваши действия и
            настройки, а также собирать обезличенную статистику посещений.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">2. Какие cookie мы используем</h2>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong>Технические (необходимые)</strong> — обеспечивают работу сайта: вход в
              аккаунт, сохранение сессии и ваш выбор по cookie. Без них сайт не может
              функционировать корректно, поэтому они используются всегда.
            </li>
            <li>
              <strong>Аналитические</strong> — сервис «Яндекс.Метрика» (счётчик № 87721057),
              включая вебвизор и карту кликов. Собирают обезличенные данные о посещаемости и
              поведении на сайте. Подключаются <strong>только после вашего согласия</strong>.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">3. Цели использования</h2>
          <p>
            Анализ посещаемости, оценка удобства и улучшение работы сайта, выявление и
            устранение ошибок. Данные обрабатываются в обезличенном виде и не используются для
            идентификации конкретного пользователя.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">4. Согласие</h2>
          <p>
            При первом посещении сайт показывает баннер с предложением принять или отклонить
            использование аналитических cookie. Аналитика включается только при нажатии
            «Принять». Если вы выбрали «Отклонить», Яндекс.Метрика не загружается.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">5. Как изменить или отозвать согласие</h2>
          <ul className="list-disc space-y-2 pl-5">
            <li>Ссылка <strong>«Настройки cookie»</strong> в подвале сайта — открыть баннер и изменить выбор.</li>
            <li>Настройки вашего браузера — запрет или удаление файлов cookie.</li>
            <li>
              Блокировщик Яндекс.Метрики:{" "}
              <a
                href="https://yandex.ru/support/metrica/general/opt-out.html"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-brand hover:text-brand-dark"
              >
                инструкция Яндекса
              </a>
              .
            </li>
          </ul>
        </section>

        <section>
          <h2 className="mb-2 text-[20px] font-semibold text-ink">6. Контакты</h2>
          <p>
            По вопросам обработки данных: <strong>[указать наименование организации / ИП]</strong>,
            эл. почта <strong>[указать контактный e-mail]</strong>.
          </p>
          <p className="mt-2 text-[13px] text-muted">
            Реквизиты и контакты заполняются владельцем сайта.
          </p>
        </section>
      </article>
    </div>
  );
}
