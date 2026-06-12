import Link from "next/link";
import type { PlantListItem } from "@/lib/api";

export function PlantCard({ plant }: { plant: PlantListItem }) {
  return (
    <Link
      href={`/plant/${plant.id_plant}`}
      className="group flex flex-col overflow-hidden rounded-card border border-line bg-white transition-shadow hover:shadow-[0_8px_24px_rgba(48,98,59,0.12)]"
    >
      <div className="relative grid aspect-4/3 place-items-center overflow-hidden bg-surface text-brand-muted">
        {plant.main_photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={plant.main_photo}
            alt={plant.name}
            className="size-full object-cover"
            loading="lazy"
          />
        ) : (
          <LeafGlyph />
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4">
        <h3 className="text-[18px] font-semibold leading-tight text-ink group-hover:text-brand">
          {plant.name}
        </h3>
        <p className="text-[14px] italic text-muted">{plant.lat_name_unique}</p>
        <div className="mt-auto flex items-center justify-between pt-3 text-[14px]">
          <span className="text-accent-ink">{plant.family}</span>
          {plant.usda_zone != null && (
            <span className="rounded-control bg-surface px-2.5 py-1 text-accent-ink">
              Зона {plant.usda_zone}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}

function LeafGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-12" fill="currentColor" aria-hidden>
      <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
    </svg>
  );
}
