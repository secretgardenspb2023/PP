import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPlant, type PlantDetail } from "@/lib/api";
import { Reveal } from "@/components/Reveal";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const p = await getPlant(id, { cache: "no-store" });
    return { title: `${p.name} (${p.lat_name_unique}) — PoiskPlant` };
  } catch {
    return { title: "Растение — PoiskPlant" };
  }
}

type Key = keyof PlantDetail["characteristics"];

// Characteristics grouped into themed section cards.
const GROUPS: { title: string; fields: [Key, string][] }[] = [
  {
    title: "Внешний вид",
    fields: [
      ["habit_forms", "Форма роста"],
      ["leaf_shapes", "Форма листа"],
      ["flower_forms", "Форма цветка"],
      ["flower_colors", "Цвет цветка"],
      ["leaf_colors", "Цвет листвы"],
      ["vegetation_periods", "Период вегетации"],
      ["flowering_months", "Цветение"],
      ["fruiting_months", "Плодоношение"],
    ],
  },
  {
    title: "Уход",
    fields: [
      ["sun", "Освещение"],
      ["soil_acidity", "Кислотность почвы"],
      ["care_levels", "Уровень ухода"],
      ["propagation", "Размножение"],
    ],
  },
  {
    title: "Дизайн сада",
    fields: [
      ["design_uses", "Использование"],
      ["garden_styles", "Стили сада"],
      ["fruit_uses", "Использование плодов"],
      ["designers", "Селекционер"],
    ],
  },
];

const FLAG_FIELDS: [Key, string][] = [
  ["is_thorny", "Колючее"],
  ["is_toxic", "Ядовито"],
  ["is_allergen", "Аллерген"],
  ["has_aroma", "Ароматное"],
  ["is_self_fertile", "Самоплодное"],
  ["has_decorative_bark", "Декоративная кора"],
  ["has_decorative_fruit", "Декоративные плоды"],
  ["soil_demanding", "Требовательно к почве"],
  ["disease_resistant", "Устойчиво к болезням"],
  ["pest_resistant", "Устойчиво к вредителям"],
  ["no_shelter", "Зимует без укрытия"],
  ["city_tolerant", "Переносит город"],
  ["no_digging", "Без выкопки"],
  ["no_watering", "Засухоустойчиво"],
];

const DESC_FIELDS: [keyof PlantDetail["descriptions"], string][] = [
  ["requirements", "Требования"],
  ["problems", "Проблемы"],
  ["diseases_pests", "Болезни и вредители"],
  ["propagation", "Размножение"],
  ["usage", "Использование"],
];

const SYN_LEVEL: Record<string, string> = { genus: "Род", species: "Вид", plant: "Растение" };

function arr(c: PlantDetail["characteristics"], k: Key): string[] {
  const v = c[k];
  return Array.isArray(v) ? (v as string[]) : [];
}

export default async function PlantPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let plant: PlantDetail;
  try {
    plant = await getPlant(id, { cache: "no-store" });
  } catch {
    notFound();
  }

  const c = plant.characteristics;
  const tax = plant.taxonomy;
  const mainPhoto = plant.photos.find((p) => p.is_main) ?? plant.photos[0];
  const flags = FLAG_FIELDS.filter(([k]) => c[k] === true);
  const sizes = (
    [
      ["Высота, до", c.height_max_cm, "см"],
      ["Диаметр, до", c.diameter_max_cm, "см"],
      ["Годовой прирост", c.annual_growth_cm, "см"],
    ] as [string, number | null | undefined, string][]
  ).filter(([, v]) => v != null);
  const groups = GROUPS.map((g) => ({
    ...g,
    fields: g.fields.filter(([k]) => arr(c, k).length),
  })).filter((g) => g.fields.length);
  const descs = DESC_FIELDS.filter(([k]) => plant.descriptions[k]);

  return (
    <div className="container-page py-8">
      <nav className="mb-6 flex flex-wrap items-center gap-1.5 text-[14px] text-muted">
        <Link href="/" className="hover:text-brand">Главная</Link>
        <span>/</span>
        <Link href="/catalog" className="hover:text-brand">Каталог</Link>
        <span>/</span>
        <span className="text-accent-ink">{plant.name}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[440px_1fr]">
        {/* Left: photo + quick facts (sticky on desktop) */}
        <div className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <Reveal>
            <div className="grid aspect-square place-items-center overflow-hidden rounded-card border border-line bg-surface shadow-soft">
              {mainPhoto?.public_url || mainPhoto?.preview_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={mainPhoto.public_url ?? mainPhoto.preview_url ?? ""}
                  alt={plant.name}
                  className="size-full object-cover"
                />
              ) : (
                <svg viewBox="0 0 24 24" className="size-24 text-brand-muted" fill="currentColor" aria-hidden>
                  <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
                </svg>
              )}
            </div>
          </Reveal>

          {plant.photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {plant.photos.slice(0, 6).map((p) => (
                <div key={p.id} className="size-16 shrink-0 overflow-hidden rounded-xl border border-line">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={p.preview_url ?? p.public_url ?? ""} alt="" className="size-full object-cover" />
                </div>
              ))}
            </div>
          )}

          <Reveal delay={80}>
            <dl className="rounded-card border border-line bg-white p-5 shadow-soft">
              {plant.usda_zone != null && <Row label="Зона USDA">{plant.usda_zone}</Row>}
              {tax.family_rus && (
                <Row label="Семейство">
                  {tax.family_rus}
                  {tax.family_lat ? <span className="text-muted"> · {tax.family_lat}</span> : null}
                </Row>
              )}
              {sizes.map(([l, v, u]) => (
                <Row key={l} label={l}>{v} {u}</Row>
              ))}
            </dl>
          </Reveal>
        </div>

        {/* Right: header + matrix */}
        <div className="min-w-0 space-y-8">
          <Reveal as="header">
            <h1 className="text-[32px] font-bold leading-tight text-ink md:text-[44px]">{plant.name}</h1>
            <p className="mt-1.5 text-[18px] italic text-muted">{plant.lat_name_unique}</p>
            {flags.length > 0 && (
              <div className="mt-5 flex flex-wrap gap-2">
                {flags.map(([k, label]) => (
                  <span key={String(k)} className="rounded-control border border-brand/20 bg-brand/8 px-3 py-1 text-[13px] font-medium text-brand-dark">
                    {label}
                  </span>
                ))}
              </div>
            )}
          </Reveal>

          {(plant.descriptions.text || plant.descriptions.facts) && (
            <Reveal>
              <section className="rounded-card border border-line bg-white p-6 shadow-soft">
                {plant.descriptions.text && (
                  <p className="whitespace-pre-line text-[16px] leading-relaxed text-accent-ink">
                    {plant.descriptions.text}
                  </p>
                )}
                {plant.descriptions.facts && (
                  <div className="mt-5">
                    <h3 className="mb-1.5 text-[18px] font-semibold text-ink">Интересные факты</h3>
                    <p className="whitespace-pre-line text-[16px] leading-relaxed text-accent-ink">
                      {plant.descriptions.facts}
                    </p>
                  </div>
                )}
              </section>
            </Reveal>
          )}

          {groups.map((g, gi) => (
            <Reveal key={g.title} delay={gi * 60}>
              <section className="rounded-card border border-line bg-white p-6 shadow-soft">
                <h2 className="mb-4 text-[20px] font-semibold text-ink">{g.title}</h2>
                <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
                  {g.fields.map(([k, label]) => (
                    <div key={String(k)}>
                      <dt className="mb-1 text-[13px] uppercase tracking-wide text-muted">{label}</dt>
                      <dd className="flex flex-wrap gap-1.5">
                        {arr(c, k).map((v) => (
                          <span key={v} className="rounded-control bg-surface px-2.5 py-1 text-[14px] text-ink">{v}</span>
                        ))}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            </Reveal>
          ))}

          {descs.length > 0 && (
            <Reveal>
              <section className="rounded-card border border-line bg-white p-6 shadow-soft">
                <div className="space-y-5">
                  {descs.map(([k, label]) => (
                    <div key={String(k)}>
                      <h3 className="mb-1.5 text-[18px] font-semibold text-ink">{label}</h3>
                      <p className="whitespace-pre-line text-[16px] leading-relaxed text-accent-ink">
                        {plant.descriptions[k]}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            </Reveal>
          )}

          {plant.synonyms.length > 0 && (
            <Reveal>
              <section className="rounded-card border border-line bg-white p-6 shadow-soft">
                <h2 className="mb-4 text-[20px] font-semibold text-ink">Синонимы</h2>
                <ul className="flex flex-wrap gap-2">
                  {plant.synonyms.map((s, i) => (
                    <li key={i} className="rounded-control border border-line px-3 py-1.5 text-[14px] text-accent-ink">
                      <span className="italic">{s.full_name || s.synonym_name}</span>
                      <span className="ml-1.5 text-muted">· {SYN_LEVEL[s.level] ?? s.level}</span>
                    </li>
                  ))}
                </ul>
              </section>
            </Reveal>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line py-2.5 last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-ink">{children}</dd>
    </div>
  );
}
