import type { Metadata } from "next";
import { listPlants, getFacets } from "@/lib/api";
import { PlantCard } from "@/components/PlantCard";
import { Filters } from "@/components/catalog/Filters";
import { SortSelect } from "@/components/catalog/SortSelect";
import { Pagination } from "@/components/catalog/Pagination";
import { CatalogSearch } from "@/components/catalog/CatalogSearch";
import { AlphabetNav } from "@/components/catalog/AlphabetNav";
import { Reveal } from "@/components/Reveal";

export const metadata: Metadata = {
  title: "Каталог растений — PoiskPlant",
  description: "Поиск и фасетные фильтры по справочнику растений.",
};

// Query keys forwarded to the catalog API (see backend filters.py).
const FILTER_KEYS = [
  "q", "sort", "page", "usda_zone",
  "leaf_shape", "habit_form", "flower_form", "sun", "soil_acid", "propagation",
  "care_level", "design_use", "garden_style", "designer", "fruit_use",
  "flower_color", "leaf_color", "vegetation_period", "flowering_month", "fruiting_month",
  "is_thorny", "is_toxic", "has_aroma",
  "height_min", "height_max", "diameter_min", "diameter_max", "growth_min", "growth_max",
  "letter",
];

type SP = Record<string, string | string[] | undefined>;

function pick(sp: SP): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of FILTER_KEYS) {
    const v = sp[k];
    const s = Array.isArray(v) ? v[0] : v;
    if (s) out[k] = s;
  }
  return out;
}

export default async function CatalogPage({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const params = pick(sp);
  const page = Math.max(1, parseInt(params.page ?? "1", 10) || 1);
  const view = Array.isArray(sp.view) ? sp.view[0] : sp.view;
  const isAlphabet = view === "alphabet";

  let list, facets;
  try {
    [list, facets] = await Promise.all([
      listPlants(params, { cache: "no-store" }),
      // facets endpoint ignores page/sort; pass the filter params as-is
      getFacets(params, { cache: "no-store" }),
    ]);
  } catch {
    return (
      <div className="container-page py-16 text-center text-muted">
        Каталог временно недоступен. Попробуйте позже.
      </div>
    );
  }

  // querystring without `page` for pagination links (keep alphabet mode)
  const pageParams = Object.fromEntries(Object.entries(params).filter(([k]) => k !== "page"));
  if (isAlphabet) pageParams.view = "alphabet";
  const qWithoutPage = new URLSearchParams(pageParams).toString();

  return (
    <div className="container-page py-8">
      <h1 className="mb-1 text-[26px] font-bold text-ink md:text-[32px]">
        {isAlphabet ? "Алфавитный указатель" : "Каталог растений"}
      </h1>
      <p className="mb-6 text-[16px] text-muted">
        Найдено: <span className="font-medium text-ink">{list.count.toLocaleString("ru-RU")}</span>
      </p>

      {isAlphabet && (
        <div className="mb-6">
          <AlphabetNav active={params.letter ?? ""} />
        </div>
      )}

      <div className="mb-6">
        <CatalogSearch />
      </div>

      <div className="flex flex-col gap-8 lg:flex-row">
        <Filters facets={facets} />

        <section className="min-w-0 flex-1">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[14px] text-muted">
              Показано {list.results.length} из {list.count.toLocaleString("ru-RU")}
            </span>
            <SortSelect />
          </div>

          {list.results.length > 0 ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {list.results.map((p, i) => (
                <Reveal key={p.id_plant} delay={Math.min(i, 6) * 50}>
                  <PlantCard plant={p} />
                </Reveal>
              ))}
            </div>
          ) : (
            <p className="rounded-card border border-line bg-surface p-8 text-center text-muted">
              Ничего не найдено. Измените запрос или сбросьте фильтры.
            </p>
          )}

          <Pagination
            page={page}
            hasPrev={Boolean(list.previous)}
            hasNext={Boolean(list.next)}
            query={qWithoutPage}
          />
        </section>
      </div>
    </div>
  );
}
