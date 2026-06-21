import Link from "next/link";
import { HeaderAuth } from "@/components/HeaderAuth";
import { HeaderSearch } from "@/components/HeaderSearch";

const NAV = [
  { label: "Каталог", href: "/catalog" },
  { label: "Алфавит", href: "/catalog?view=alphabet" },
  { label: "О проекте", href: "/about" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-white/80 backdrop-blur-md">
      <div className="container-page flex h-18 items-center gap-5">
        <Link href="/" className="flex shrink-0 items-center gap-2 transition-transform hover:scale-[1.02]">
          <LeafMark />
          <span className="font-heading text-xl font-bold tracking-tight text-brand-dark">
            Poisk<span className="text-brand">Plant</span>
          </span>
        </Link>

        <HeaderSearch />

        <button
          type="button"
          className="hidden shrink-0 items-center gap-1 text-[15px] text-accent-ink transition-colors hover:text-ink lg:flex"
        >
          <PinIcon className="size-4 text-brand" />
          Санкт-Петербург
        </button>

        <nav className="hidden items-center gap-6 xl:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="relative text-[15px] text-accent-ink transition-colors after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-0 after:rounded-full after:bg-brand after:transition-all after:duration-300 after:ease-out hover:text-brand-dark hover:after:w-full"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <HeaderAuth />
      </div>
    </header>
  );
}

function LeafMark() {
  return (
    <span className="grid size-9 place-items-center rounded-2xl bg-linear-to-br from-brand-light to-brand text-white shadow-soft">
      <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
        <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
      </svg>
    </span>
  );
}

function PinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden>
      <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z" />
    </svg>
  );
}
