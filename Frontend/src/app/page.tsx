import Link from "next/link";
import { PlantCard } from "@/components/PlantCard";
import { Reveal } from "@/components/Reveal";
import { listPlants } from "@/lib/api";

export const dynamic = "force-dynamic";

async function popularPlants() {
  try {
    const data = await listPlants({ sort: "name" }, { cache: "no-store" });
    return data.results.slice(0, 8);
  } catch {
    return [];
  }
}

const FEATURES = [
  { t: "Умный поиск", d: "По русским и латинским названиям — с учётом морфологии, опечаток и синонимов." },
  { t: "Фасетные фильтры", d: "Подбор по освещению, почве, уходу, дизайну сада и десяткам других параметров." },
  { t: "Полные карточки", d: "Характеристики, уход, дизайн, фото и синонимы — всё в одном месте." },
];

export default async function Home() {
  const plants = await popularPlants();

  return (
    <>
      {/* Hero */}
      <section className="hero-glow relative overflow-hidden">
        <div className="container-page relative py-20 text-center md:py-28">
          <Reveal>
            <span className="mb-5 inline-flex items-center gap-2 rounded-control border border-brand/25 bg-white/70 px-4 py-1.5 text-[14px] font-medium text-brand-dark backdrop-blur">
              <Sprout /> 12 371 растение в справочнике
            </span>
          </Reveal>
          <Reveal delay={80}>
            <h1 className="mx-auto max-w-4xl text-[34px] font-bold leading-[1.1] text-ink md:text-[52px]">
              Электронный справочник{" "}
              <span className="bg-linear-to-r from-brand to-brand-dark bg-clip-text text-transparent">
                растений
              </span>
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-5 max-w-2xl text-[18px] leading-relaxed text-accent-ink">
              Характеристики, уход и дизайн сада для тысяч видов. Найдите растение по названию
              или подберите по параметрам.
            </p>
          </Reveal>

          <Reveal delay={240}>
            <form
              action="/catalog"
              className="mx-auto mt-9 flex max-w-2xl items-center gap-2 rounded-control border border-line bg-white/95 p-2 shadow-pop backdrop-blur transition-[border-color] focus-within:border-brand"
            >
              <SearchIcon className="ml-3 size-5 shrink-0 text-muted" />
              <input
                type="search"
                name="q"
                placeholder="Например, дуб черешчатый или Quercus robur"
                aria-label="Поиск растения"
                className="h-11 flex-1 bg-transparent text-[16px] outline-none placeholder:text-muted"
              />
              <button type="submit" className="btn-primary h-11 px-7">Найти</button>
            </form>
          </Reveal>
        </div>
      </section>

      {/* Catalog preview */}
      <section className="container-page py-14 md:py-20">
        <Reveal as="div" className="mb-7 flex items-end justify-between gap-4">
          <h2 className="text-[28px] font-bold text-ink md:text-[36px]">Растения каталога</h2>
          <Link href="/catalog" className="group inline-flex items-center gap-1 text-[16px] font-medium text-brand transition-colors hover:text-brand-dark">
            Весь каталог
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
        </Reveal>

        {plants.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {plants.map((plant, i) => (
              <Reveal key={plant.id_plant} delay={i * 70}>
                <PlantCard plant={plant} />
              </Reveal>
            ))}
          </div>
        ) : (
          <p className="rounded-card border border-line bg-surface p-8 text-center text-muted">
            Каталог временно недоступен. Попробуйте обновить страницу позже.
          </p>
        )}
      </section>

      {/* Features */}
      <section className="bg-surface py-16 md:py-20">
        <div className="container-page">
          <div className="grid gap-6 md:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.t} delay={i * 90}>
                <div className="h-full rounded-card border border-line bg-white p-7 shadow-soft transition-[transform,box-shadow] duration-300 ease-out hover:-translate-y-1 hover:shadow-card">
                  <div className="mb-4 grid size-12 place-items-center rounded-2xl bg-linear-to-br from-brand-light/30 to-brand/15 text-brand-dark">
                    <Sprout />
                  </div>
                  <h3 className="text-[20px] font-semibold text-ink">{f.t}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-accent-ink">{f.d}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.2-3.2" strokeLinecap="round" />
    </svg>
  );
}

function Sprout() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
      <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
    </svg>
  );
}
