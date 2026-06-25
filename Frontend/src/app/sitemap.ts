import type { MetadataRoute } from "next";

// Карта сайта (SEO, ТЗ этап 8). Базовый адрес — боевой домен; список карточек
// тянем с бэкенда по внутреннему адресу (как остальные SSR-запросы, с
// X-Forwarded-Proto, иначе SECURE_SSL_REDIRECT даёт 302).
const SITE = "https://poiskplant.ru";
const API = process.env.API_BASE ?? "http://backend:8000/api/v1";

// Генерируем при запросе (не на сборке — там бэкенд недоступен). Список слагов
// бэкенд кэширует в Redis на час, так что это дёшево.
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE}/catalog`, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE}/about`, changeFrequency: "monthly", priority: 0.4 },
  ];
  try {
    const res = await fetch(`${API}/plants/sitemap/`, {
      headers: { "X-Forwarded-Proto": "https" },
      cache: "no-store",
    });
    if (!res.ok) return staticRoutes;
    const items: { slug: string; updated?: string | null }[] = await res.json();
    const plantRoutes: MetadataRoute.Sitemap = items
      .filter((it) => it.slug)
      .map((it) => ({
        url: `${SITE}/plant/${encodeURIComponent(it.slug)}`,
        lastModified: it.updated ? new Date(it.updated) : undefined,
        changeFrequency: "weekly",
        priority: 0.7,
      }));
    return [...staticRoutes, ...plantRoutes];
  } catch {
    return staticRoutes;
  }
}
