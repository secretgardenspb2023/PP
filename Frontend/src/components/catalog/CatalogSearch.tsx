"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";

// Search box that merges the query into the current filters (keeps facets).
export function CatalogSearch() {
  const router = useRouter();
  const sp = useSearchParams();
  const [value, setValue] = useState(sp.get("q") ?? "");

  useEffect(() => {
    setValue(sp.get("q") ?? "");
  }, [sp]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const params = new URLSearchParams(sp.toString());
        if (value.trim()) params.set("q", value.trim());
        else params.delete("q");
        params.delete("page");
        router.push(`/catalog?${params.toString()}`);
      }}
      className="flex items-center gap-2 rounded-control border border-line bg-white p-1.5 focus-within:border-brand"
    >
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Поиск по названию (рус/лат)…"
        aria-label="Поиск растения"
        className="h-10 flex-1 bg-transparent pl-3 text-[16px] outline-none placeholder:text-muted"
      />
      <button
        type="submit"
        className="h-10 rounded-control bg-brand px-5 font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
      >
        Найти
      </button>
    </form>
  );
}
