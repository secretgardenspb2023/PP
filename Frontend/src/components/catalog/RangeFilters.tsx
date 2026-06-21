"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Histogram, Histograms } from "@/lib/api";

// Диапазонные фильтры со столбиками распределения и двуручным ползунком (ТЗ 5.5/5.14):
// гистограмма показывает, сколько растений в каждом интервале; ползунок и поля «от/до»
// сужают выбор и пишутся в URL.
const RANGES = [
  { key: "height", label: "Высота, см" },
  { key: "diameter", label: "Диаметр, см" },
  { key: "growth", label: "Прирост в год, см" },
];

function RangeBlock({ k, label, h }: { k: string; label: string; h: Histogram }) {
  const router = useRouter();
  const sp = useSearchParams();
  const min = Math.floor(h.min ?? 0);
  const max = Math.ceil(h.max ?? 0);

  const curMin = sp.get(`${k}_min`);
  const curMax = sp.get(`${k}_max`);
  const [lo, setLo] = useState(curMin != null ? Number(curMin) : min);
  const [hi, setHi] = useState(curMax != null ? Number(curMax) : max);
  useEffect(() => {
    setLo(curMin != null ? Number(curMin) : min);
    setHi(curMax != null ? Number(curMax) : max);
  }, [curMin, curMax, min, max]);

  const span = Math.max(1, max - min);
  const pct = (v: number) => ((Math.min(max, Math.max(min, v)) - min) / span) * 100;
  const maxCount = Math.max(1, ...h.buckets.map((b) => b.count));

  function apply(nlo = lo, nhi = hi) {
    const params = new URLSearchParams(sp.toString());
    const put = (name: string, on: boolean, v: number) =>
      on ? params.set(name, String(v)) : params.delete(name);
    put(`${k}_min`, nlo > min, nlo);
    put(`${k}_max`, nhi < max, nhi);
    params.delete("page");
    router.push(`/catalog?${params.toString()}`);
  }

  if (max <= min) return null;

  return (
    <details open className="group px-4 py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between text-[16px] font-medium text-ink">
        <span>{label}</span>
        <span className="text-muted transition-transform group-open:rotate-180">⌄</span>
      </summary>
      <div className="mt-3">
        {/* Гистограмма распределения */}
        <div className="flex h-12 items-end gap-px" aria-hidden>
          {h.buckets.map((b, i) => {
            const inRange = b.to >= lo && b.from <= hi;
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

        {/* Двуручный ползунок */}
        <div className="relative mt-3 h-5">
          <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded bg-line" />
          <div
            className="absolute top-1/2 h-1 -translate-y-1/2 rounded bg-brand"
            style={{ left: `${pct(lo)}%`, right: `${100 - pct(hi)}%` }}
          />
          <input
            type="range"
            className="rng"
            min={min}
            max={max}
            value={lo}
            onChange={(e) => setLo(Math.min(Number(e.target.value), hi))}
            onPointerUp={() => apply()}
            onKeyUp={(e) => e.key === "Enter" && apply()}
            aria-label={`${label}: от`}
          />
          <input
            type="range"
            className="rng"
            min={min}
            max={max}
            value={hi}
            onChange={(e) => setHi(Math.max(Number(e.target.value), lo))}
            onPointerUp={() => apply()}
            onKeyUp={(e) => e.key === "Enter" && apply()}
            aria-label={`${label}: до`}
          />
        </div>

        {/* Числовые поля «от/до» */}
        <div className="mt-3 flex items-center gap-2">
          <input
            type="number"
            inputMode="numeric"
            value={lo}
            onChange={(e) => setLo(Number(e.target.value))}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            className="h-9 w-full rounded-control border border-line px-2 text-[14px] outline-none focus:border-brand"
            aria-label={`${label}: от (число)`}
          />
          <span className="text-muted">–</span>
          <input
            type="number"
            inputMode="numeric"
            value={hi}
            onChange={(e) => setHi(Number(e.target.value))}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            className="h-9 w-full rounded-control border border-line px-2 text-[14px] outline-none focus:border-brand"
            aria-label={`${label}: до (число)`}
          />
          <button
            type="button"
            onClick={() => apply()}
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
