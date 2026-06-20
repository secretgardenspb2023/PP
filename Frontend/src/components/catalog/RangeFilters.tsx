"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Histogram, Histograms } from "@/lib/api";

// Диапазонные фильтры с гистограммой распределения (ТЗ 5.14): столбики показывают,
// сколько растений в каждом интервале; поля «от/до» сужают выбор и пишутся в URL.
const RANGES = [
  { key: "height", label: "Высота, см" },
  { key: "diameter", label: "Диаметр, см" },
  { key: "growth", label: "Прирост в год, см" },
];

function RangeBlock({ k, label, h }: { k: string; label: string; h: Histogram }) {
  const router = useRouter();
  const sp = useSearchParams();
  const curMin = sp.get(`${k}_min`) ?? "";
  const curMax = sp.get(`${k}_max`) ?? "";
  const [lo, setLo] = useState(curMin);
  const [hi, setHi] = useState(curMax);
  useEffect(() => {
    setLo(curMin);
    setHi(curMax);
  }, [curMin, curMax]);

  const maxCount = Math.max(1, ...h.buckets.map((b) => b.count));

  function apply() {
    const params = new URLSearchParams(sp.toString());
    const put = (name: string, v: string) =>
      v.trim() ? params.set(name, v.trim()) : params.delete(name);
    put(`${k}_min`, lo);
    put(`${k}_max`, hi);
    params.delete("page");
    router.push(`/catalog?${params.toString()}`);
  }

  return (
    <details open className="group px-4 py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between text-[16px] font-medium text-ink">
        <span>{label}</span>
        <span className="text-muted transition-transform group-open:rotate-180">⌄</span>
      </summary>
      <div className="mt-3">
        <div className="flex h-12 items-end gap-px" aria-hidden>
          {h.buckets.map((b, i) => {
            const inRange = (!lo || b.to >= Number(lo)) && (!hi || b.from <= Number(hi));
            return (
              <div
                key={i}
                title={`${Math.round(b.from)}–${Math.round(b.to)}: ${b.count}`}
                className={"flex-1 rounded-sm " + (inRange ? "bg-brand/70" : "bg-line")}
                style={{ height: `${Math.max(4, (b.count / maxCount) * 100)}%` }}
              />
            );
          })}
        </div>
        <div className="mt-2 flex items-center gap-2">
          <input
            type="number"
            inputMode="numeric"
            value={lo}
            onChange={(e) => setLo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            placeholder={h.min != null ? String(Math.floor(h.min)) : "от"}
            className="h-9 w-full rounded-control border border-line px-2 text-[14px] outline-none focus:border-brand"
            aria-label={`${label}: от`}
          />
          <span className="text-muted">–</span>
          <input
            type="number"
            inputMode="numeric"
            value={hi}
            onChange={(e) => setHi(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            placeholder={h.max != null ? String(Math.ceil(h.max)) : "до"}
            className="h-9 w-full rounded-control border border-line px-2 text-[14px] outline-none focus:border-brand"
            aria-label={`${label}: до`}
          />
          <button
            type="button"
            onClick={apply}
            className="h-9 shrink-0 rounded-control bg-brand px-3 text-[14px] font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark"
          >
            OK
          </button>
        </div>
      </div>
    </details>
  );
}

export function RangeFilters({ histograms }: { histograms: Histograms }) {
  const active = RANGES.filter((r) => histograms[r.key]?.buckets?.length);
  if (!active.length) return null;
  return (
    <div className="mt-4">
      <h3 className="mb-2 text-[15px] font-semibold text-muted">Размеры</h3>
      <div className="divide-y divide-line rounded-card border border-line bg-white shadow-soft">
        {active.map((r) => (
          <RangeBlock key={r.key} k={r.key} label={r.label} h={histograms[r.key]} />
        ))}
      </div>
    </div>
  );
}
