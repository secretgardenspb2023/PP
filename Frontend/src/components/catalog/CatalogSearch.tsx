"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { suggest, type Suggestion } from "@/lib/api";

// Search box with live autosuggest (debounce 200ms, ТЗ 5.7/5.10). Submitting
// runs a full catalog search; picking a suggestion opens that plant's card.
export function CatalogSearch() {
  const router = useRouter();
  const sp = useSearchParams();
  const [value, setValue] = useState(sp.get("q") ?? "");
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setValue(sp.get("q") ?? "");
  }, [sp]);

  // Debounced suggestions.
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

  // Close on outside click.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function submit(q: string) {
    const params = new URLSearchParams(sp.toString());
    if (q.trim()) params.set("q", q.trim());
    else params.delete("q");
    params.delete("page");
    setOpen(false);
    router.push(`/catalog?${params.toString()}`);
  }

  return (
    <div ref={boxRef} className="relative">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="flex items-center gap-2 rounded-control border border-line bg-white p-1.5 focus-within:border-brand"
      >
        <input
          type="search"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => items.length && setOpen(true)}
          placeholder="Поиск по названию (рус/лат)…"
          aria-label="Поиск растения"
          autoComplete="off"
          className="h-10 flex-1 bg-transparent pl-3 text-[16px] outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          className="h-10 rounded-control bg-brand px-5 font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
        >
          Найти
        </button>
      </form>

      {open && items.length > 0 && (
        <ul className="absolute z-30 mt-1.5 max-h-80 w-full overflow-auto rounded-card border border-line bg-white py-1 shadow-soft">
          {items.map((s) => (
            <li key={s.id_plant}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setOpen(false);
                  router.push(`/plant/${s.id_plant}`);
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
