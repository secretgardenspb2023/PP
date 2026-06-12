"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import type { Facets } from "@/lib/api";

// Dimension -> Russian title. Order here drives display order.
const LABELS: Record<string, string> = {
  sun: "Освещение",
  soil_acid: "Кислотность почвы",
  care_level: "Уровень ухода",
  habit_form: "Форма роста",
  flower_color: "Цвет цветка",
  leaf_color: "Цвет листвы",
  flower_form: "Форма цветка",
  leaf_shape: "Форма листа",
  design_use: "Использование в дизайне",
  garden_style: "Стиль сада",
  fruit_use: "Использование плодов",
  propagation: "Размножение",
  flowering_month: "Месяцы цветения",
  fruiting_month: "Месяцы плодоношения",
  vegetation_period: "Период вегетации",
  designer: "Селекционер",
};

function parseList(v: string | null): string[] {
  return v ? v.split(",").filter(Boolean) : [];
}

export function Filters({ facets }: { facets: Facets }) {
  const router = useRouter();
  const sp = useSearchParams();

  const activeCount = Object.keys(LABELS).reduce(
    (n, dim) => n + parseList(sp.get(dim)).length,
    0,
  );

  const toggle = useCallback(
    (dim: string, value: string) => {
      const current = parseList(sp.get(dim));
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      const params = new URLSearchParams(sp.toString());
      if (next.length) params.set(dim, next.join(","));
      else params.delete(dim);
      params.delete("page"); // reset paging on filter change
      router.push(`/catalog?${params.toString()}`);
    },
    [router, sp],
  );

  const dims = Object.keys(LABELS).filter((d) => facets[d]?.length);

  return (
    <aside className="w-full shrink-0 lg:w-64">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-heading text-[20px] font-semibold text-ink">Фильтры</h2>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={() => router.push(`/catalog?${keepText(sp)}`)}
            className="text-[14px] text-brand hover:text-brand-dark"
          >
            Сбросить ({activeCount})
          </button>
        )}
      </div>

      <div className="divide-y divide-line rounded-card border border-line bg-white shadow-soft">
        {dims.map((dim, i) => {
          const selected = parseList(sp.get(dim));
          return (
            <details key={dim} open={i < 4} className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-[16px] font-medium text-ink">
                <span>
                  {LABELS[dim]}
                  {selected.length > 0 && (
                    <span className="ml-1.5 rounded-control bg-brand px-1.5 py-0.5 text-[12px] text-white">
                      {selected.length}
                    </span>
                  )}
                </span>
                <span className="text-muted transition-transform group-open:rotate-180">⌄</span>
              </summary>
              <ul className="max-h-64 space-y-1 overflow-auto px-4 pb-3">
                {facets[dim].map((f) => (
                  <li key={f.value}>
                    <label className="flex cursor-pointer items-center gap-2 py-1 text-[14px] text-accent-ink hover:text-ink">
                      <input
                        type="checkbox"
                        checked={selected.includes(f.value)}
                        onChange={() => toggle(dim, f.value)}
                        className="size-4 accent-brand"
                      />
                      <span className="flex-1">{f.value}</span>
                      <span className="text-muted">{f.count}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </details>
          );
        })}
      </div>
    </aside>
  );
}

// keep only the text query when resetting filters
function keepText(sp: URLSearchParams): string {
  const params = new URLSearchParams();
  const q = sp.get("q");
  const sort = sp.get("sort");
  if (q) params.set("q", q);
  if (sort) params.set("sort", sort);
  return params.toString();
}
