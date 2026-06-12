import Link from "next/link";
import { HeaderAuth } from "@/components/HeaderAuth";

const NAV = [
  { label: "Каталог", href: "/catalog" },
  { label: "Алфавит", href: "/catalog?view=alphabet" },
  { label: "О проекте", href: "/about" },
];

export function Header() {
  return (
    <header className="border-b border-line bg-white">
      <div className="container-page flex h-18 items-center gap-6">
        {/* Logo */}
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <LeafMark />
          <span className="font-heading text-xl font-bold text-brand-dark">
            Poisk<span className="text-brand">Plant</span>
          </span>
        </Link>

        {/* Search */}
        <form action="/catalog" className="relative hidden flex-1 md:block">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted" />
          <input
            type="search"
            name="q"
            placeholder="Поиск растения по названию…"
            aria-label="Поиск растения"
            className="h-11 w-full rounded-control border border-line bg-surface pl-11 pr-4 text-[16px] outline-none transition-colors placeholder:text-muted focus:border-brand focus:bg-white"
          />
        </form>

        {/* City */}
        <button
          type="button"
          className="hidden shrink-0 items-center gap-1 text-[16px] text-accent-ink hover:text-ink lg:flex"
        >
          <PinIcon className="size-4 text-brand" />
          Санкт-Петербург
        </button>

        {/* Nav */}
        <nav className="hidden items-center gap-5 xl:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[16px] text-accent-ink transition-colors hover:text-brand"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Auth (dynamic) */}
        <HeaderAuth />
      </div>
    </header>
  );
}

function LeafMark() {
  return (
    <span className="grid size-9 place-items-center rounded-control bg-brand text-white">
      <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
        <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
      </svg>
    </span>
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

function PinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden>
      <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z" />
    </svg>
  );
}
