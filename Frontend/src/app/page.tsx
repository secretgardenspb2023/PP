import Link from "next/link";
import { PlantCard } from "@/components/PlantCard";
import { listPlants } from "@/lib/api";

export const dynamic = "force-dynamic"; // always render with fresh catalog data

async function popularPlants() {
  try {
    const data = await listPlants({ sort: "name" }, { cache: "no-store" });
    return data.results.slice(0, 8);
  } catch {
    return [];
  }
}

export default async function Home() {
  const plants = await popularPlants();

  return (
    <>
      {/* Hero */}
      <section className="bg-surface">
        <div className="container-page py-16 text-center md:py-24">
          <h1 className="mx-auto max-w-3xl text-[32px] font-bold leading-tight text-ink md:text-[40px]">
            Электронный справочник растений
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-[18px] text-accent-ink">
            Более 12 000 карточек: характеристики, уход, дизайн сада. Поиск по русским
            и латинским названиям с учётом морфологии и опечаток.
          </p>

          <form
            action="/catalog"
            className="mx-auto mt-8 flex max-w-2xl items-center gap-2 rounded-control border border-line bg-white p-1.5 shadow-sm focus-within:border-brand"
          >
            <input
              type="search"
              name="q"
              placeholder="Например, дуб черешчатый или Quercus robur"
              aria-label="Поиск растения"
              className="h-11 flex-1 bg-transparent pl-4 text-[16px] outline-none placeholder:text-muted"
            />
            <button
              type="submit"
              className="h-11 rounded-control bg-brand px-6 font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
            >
              Найти
            </button>
          </form>
        </div>
      </section>

      {/* Catalog preview */}
      <section className="container-page py-12 md:py-16">
        <div className="mb-6 flex items-end justify-between">
          <h2 className="text-[26px] font-bold text-ink md:text-[32px]">Растения каталога</h2>
          <Link href="/catalog" className="text-[16px] font-medium text-brand hover:text-brand-dark">
            Весь каталог →
          </Link>
        </div>

        {plants.length > 0 ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {plants.map((plant) => (
              <PlantCard key={plant.id_plant} plant={plant} />
            ))}
          </div>
        ) : (
          <p className="rounded-card border border-line bg-surface p-6 text-center text-muted">
            Каталог временно недоступен. Попробуйте обновить страницу позже.
          </p>
        )}
      </section>
    </>
  );
}
