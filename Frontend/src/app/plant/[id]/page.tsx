import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPlant, type PlantDetail } from "@/lib/api";

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

const ARRAY_FIELDS: [keyof PlantDetail["characteristics"], string][] = [
  ["habit_forms", "Форма роста"],
  ["leaf_shapes", "Форма листа"],
  ["flower_forms", "Форма цветка"],
  ["flower_colors", "Цвет цветка"],
  ["leaf_colors", "Цвет листвы"],
  ["sun", "Освещение"],
  ["soil_acidity", "Кислотность почвы"],
  ["care_levels", "Уровень ухода"],
  ["propagation", "Размножение"],
  ["vegetation_periods", "Период вегетации"],
  ["flowering_months", "Цветение (месяцы)"],
  ["fruiting_months", "Плодоношение (месяцы)"],
  ["design_uses", "Использование в дизайне"],
  ["garden_styles", "Стили сада"],
  ["fruit_uses", "Использование плодов"],
  ["designers", "Селекционер"],
];

const FLAG_FIELDS: [keyof PlantDetail["characteristics"], string][] = [
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

const SYN_LEVEL: Record<string, string> = {
  genus: "Род",
  species: "Вид",
  plant: "Растение",
};

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
  const arrays = ARRAY_FIELDS.filter(([k]) => Array.isArray(c[k]) && (c[k] as string[]).length);
  const flags = FLAG_FIELDS.filter(([k]) => c[k] === true);
  const sizes = [
    ["Высота, до", c.height_max_cm, "см"],
    ["Диаметр, до", c.diameter_max_cm, "см"],
    ["Годовой прирост", c.annual_growth_cm, "см"],
  ].filter(([, v]) => v != null) as [string, number, string][];
  const descs = DESC_FIELDS.filter(([k]) => plant.descriptions[k]);

  return (
    <div className="container-page py-8">
      {/* breadcrumb */}
      <nav className="mb-4 text-[14px] text-muted">
        <Link href="/" className="hover:text-brand">Главная</Link> ·{" "}
        <Link href="/catalog" className="hover:text-brand">Каталог</Link> ·{" "}
        <span className="text-accent-ink">{plant.name}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[420px_1fr]">
        {/* Left: photo + quick facts */}
        <div className="space-y-4">
          <div className="grid aspect-square place-items-center overflow-hidden rounded-card border border-line bg-surface text-brand-muted">
            {mainPhoto?.public_url || mainPhoto?.preview_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mainPhoto.public_url ?? mainPhoto.preview_url ?? ""}
                alt={plant.name}
                className="size-full object-cover"
              />
            ) : (
              <svg viewBox="0 0 24 24" className="size-20" fill="currentColor" aria-hidden>
                <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
              </svg>
            )}
          </div>

          <dl className="rounded-card border border-line bg-white p-4 text-[15px]">
            {plant.usda_zone != null && (
              <Row label="Зона USDA">{plant.usda_zone}</Row>
            )}
            {tax.family_rus && (
              <Row label="Семейство">
                {tax.family_rus}
                {tax.family_lat ? <span className="text-muted"> · {tax.family_lat}</span> : null}
              </Row>
            )}
            {sizes.map(([l, v, u]) => (
              <Row key={l} label={l}>
                {v} {u}
              </Row>
            ))}
          </dl>
        </div>

        {/* Right: header + matrix */}
        <div className="min-w-0 space-y-8">
          <header>
            <h1 className="text-[32px] font-bold leading-tight text-ink md:text-[40px]">
              {plant.name}
            </h1>
            <p className="mt-1 text-[18px] italic text-muted">{plant.lat_name_unique}</p>
            {flags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {flags.map(([k, label]) => (
                  <span
                    key={String(k)}
                    className="rounded-control bg-surface px-3 py-1 text-[14px] text-accent-ink"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}
          </header>

          {/* Characteristics matrix */}
          {arrays.length > 0 && (
            <Section title="Характеристики">
              <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
                {arrays.map(([k, label]) => (
                  <div key={String(k)}>
                    <dt className="text-[14px] text-muted">{label}</dt>
                    <dd className="mt-0.5 flex flex-wrap gap-1.5">
                      {(c[k] as string[]).map((v) => (
                        <span
                          key={v}
                          className="rounded-control bg-surface px-2.5 py-0.5 text-[14px] text-ink"
                        >
                          {v}
                        </span>
                      ))}
                    </dd>
                  </div>
                ))}
              </dl>
            </Section>
          )}

          {/* Text blocks */}
          {descs.map(([k, label]) => (
            <Section key={String(k)} title={label}>
              <p className="whitespace-pre-line text-[16px] leading-relaxed text-accent-ink">
                {plant.descriptions[k]}
              </p>
            </Section>
          ))}

          {/* Synonyms */}
          {plant.synonyms.length > 0 && (
            <Section title="Синонимы">
              <ul className="flex flex-wrap gap-2">
                {plant.synonyms.map((s, i) => (
                  <li
                    key={i}
                    className="rounded-control border border-line px-3 py-1 text-[14px] text-accent-ink"
                  >
                    <span className="italic">{s.full_name || s.synonym_name}</span>
                    <span className="ml-1.5 text-muted">· {SYN_LEVEL[s.level] ?? s.level}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-[22px] font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line py-2 last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-ink">{children}</dd>
    </div>
  );
}
