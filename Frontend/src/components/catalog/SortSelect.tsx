"use client";

import { useRouter, useSearchParams } from "next/navigation";

const OPTIONS: { value: string; label: string }[] = [
  { value: "name", label: "По названию (А–Я)" },
  { value: "-name", label: "По названию (Я–А)" },
  { value: "new", label: "Сначала новые" },
  { value: "old", label: "Сначала старые" },
];

export function SortSelect() {
  const router = useRouter();
  const sp = useSearchParams();
  const current = sp.get("sort") ?? "name";

  return (
    <label className="flex items-center gap-2 text-[14px] text-accent-ink">
      Сортировка:
      <select
        value={current}
        onChange={(e) => {
          const params = new URLSearchParams(sp.toString());
          params.set("sort", e.target.value);
          params.delete("page");
          router.push(`/catalog?${params.toString()}`);
        }}
        className="rounded-control border border-line bg-white px-3 py-1.5 text-ink outline-none focus:border-brand"
      >
        {OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
