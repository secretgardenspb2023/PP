import Link from "next/link";

// Алфавитный навигатор справочника (ТЗ 5.17 / дизайн «алфавитный навигатор»).
// Буквы ведут на /catalog?view=alphabet&letter=X — фильтр по первой букве имени.
const RU = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ".split("");
const LAT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

function Row({ letters, active }: { letters: string[]; active: string }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {letters.map((ch) => {
        const on = active.toUpperCase() === ch;
        return (
          <Link
            key={ch}
            href={`/catalog?view=alphabet&letter=${encodeURIComponent(ch)}`}
            aria-current={on ? "page" : undefined}
            className={
              "grid size-9 place-items-center rounded-control border text-[15px] font-medium transition-colors " +
              (on
                ? "border-brand bg-brand text-white"
                : "border-line text-accent-ink hover:border-brand hover:text-brand-dark")
            }
          >
            {ch}
          </Link>
        );
      })}
    </div>
  );
}

export function AlphabetNav({ active = "" }: { active?: string }) {
  return (
    <div className="space-y-3 rounded-card border border-line bg-white p-4 shadow-soft">
      <Row letters={RU} active={active} />
      <Row letters={LAT} active={active} />
      <div className="flex items-center gap-3 pt-1">
        <Link
          href="/catalog?view=alphabet&letter=%23"
          aria-current={active === "#" ? "page" : undefined}
          className={
            "grid h-9 min-w-9 place-items-center rounded-control border px-2 text-[15px] font-medium transition-colors " +
            (active === "#"
              ? "border-brand bg-brand text-white"
              : "border-line text-accent-ink hover:border-brand hover:text-brand-dark")
          }
        >
          #
        </Link>
        <Link href="/catalog" className="text-[14px] text-brand hover:text-brand-dark">
          Показать все
        </Link>
      </div>
    </div>
  );
}
