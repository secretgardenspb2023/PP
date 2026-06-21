"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { suggest, type Suggestion } from "@/lib/api";

// Поиск в шапке с живыми подсказками (debounce 200мс). Submit → каталог,
// выбор подсказки → карточка растения. Логика как в CatalogSearch.
export function HeaderSearch() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = value.trim();
    if (q.length < 2) {
      setItems([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        setItems(await suggest(q));
        setOpen(true);
      } catch {
        setItems([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [value]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function submit(q: string) {
    setOpen(false);
    router.push(q.trim() ? `/catalog?q=${encodeURIComponent(q.trim())}` : "/catalog");
  }

  return (
    <div ref={boxRef} className="relative hidden flex-1 md:block">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => items.length && setOpen(true)}
          placeholder="Поиск растения по названию…"
          aria-label="Поиск растения"
          autoComplete="off"
          className="h-11 w-full rounded-control border border-line bg-surface pl-11 pr-4 text-[15px] outline-none transition-[border-color,box-shadow,background-color] placeholder:text-muted focus:border-brand focus:bg-white focus:shadow-[0_0_0_4px_rgba(86,183,107,0.13)]"
        />
      </form>

      {open && items.length > 0 && (
        <ul className="absolute z-50 mt-1.5 max-h-80 w-full overflow-auto rounded-card border border-line bg-white py-1 shadow-soft">
          {items.map((s) => (
            <li key={s.id_plant}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setOpen(false);
                  setValue("");
                  router.push(`/plant/${s.url_slug}`);
                }}
                className="block w-full px-4 py-2 text-left text-[15px] text-ink hover:bg-surface"
              >
                {s.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
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
