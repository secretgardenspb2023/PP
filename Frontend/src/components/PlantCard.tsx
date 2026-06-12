import Link from "next/link";
import type { PlantListItem } from "@/lib/api";

export function PlantCard({ plant }: { plant: PlantListItem }) {
  return (
    <Link
      href={`/plant/${plant.id_plant}`}
      className="group relative flex flex-col overflow-hidden rounded-card border border-line bg-white shadow-soft transition-[transform,box-shadow,border-color] duration-300 ease-out hover:-translate-y-1.5 hover:border-brand/40 hover:shadow-card"
    >
      <div className="relative aspect-4/3 overflow-hidden">
        {plant.main_photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={plant.main_photo}
            alt={plant.name}
            loading="lazy"
            className="size-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.06]"
          />
        ) : (
          <PlaceholderLeaf />
        )}
        {plant.usda_zone != null && (
          <span className="absolute right-3 top-3 rounded-control bg-white/90 px-2.5 py-1 text-[12px] font-medium text-brand-dark shadow-soft backdrop-blur">
            Зона {plant.usda_zone}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4">
        <h3 className="line-clamp-2 text-[18px] font-semibold leading-snug text-ink transition-colors group-hover:text-brand-dark">
          {plant.name}
        </h3>
        <p className="line-clamp-1 text-[14px] italic text-muted">{plant.lat_name_unique}</p>
        <div className="mt-auto flex items-center gap-2 pt-3">
          <span className="inline-flex items-center gap-1.5 text-[13px] text-accent-ink">
            <LeafDot /> {plant.family}
          </span>
        </div>
      </div>
    </Link>
  );
}

function PlaceholderLeaf() {
  return (
    <div className="grid size-full place-items-center bg-linear-to-br from-[#eef7f0] to-[#dceede] text-brand-muted">
      <svg viewBox="0 0 24 24" className="size-14 opacity-70" fill="currentColor" aria-hidden>
        <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
      </svg>
    </div>
  );
}

function LeafDot() {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5 text-brand" fill="currentColor" aria-hidden>
      <path d="M5 19C5 11 11 5 20 5c0 9-6 15-14 15-1.2 0-1.8-.5-1.8-1.5C4.2 16 7 13 11 11.5 8 14 6.5 16 6 19H5Z" />
    </svg>
  );
}
