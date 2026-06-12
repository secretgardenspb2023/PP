import Link from "next/link";

// Server component. `query` is the current querystring without `page`.
export function Pagination({
  page,
  hasPrev,
  hasNext,
  query,
}: {
  page: number;
  hasPrev: boolean;
  hasNext: boolean;
  query: string;
}) {
  if (!hasPrev && !hasNext) return null;
  const href = (p: number) => `/catalog?${query ? query + "&" : ""}page=${p}`;

  return (
    <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Постраничная навигация">
      <PageLink href={href(page - 1)} disabled={!hasPrev}>
        ← Назад
      </PageLink>
      <span className="text-[14px] text-accent-ink">Страница {page}</span>
      <PageLink href={href(page + 1)} disabled={!hasNext}>
        Вперёд →
      </PageLink>
    </nav>
  );
}

function PageLink({
  href,
  disabled,
  children,
}: {
  href: string;
  disabled: boolean;
  children: React.ReactNode;
}) {
  const cls =
    "rounded-control border px-4 py-2 text-[14px] font-medium transition-colors";
  if (disabled) {
    return (
      <span className={`${cls} cursor-not-allowed border-line text-grey-20`} aria-disabled>
        {children}
      </span>
    );
  }
  return (
    <Link href={href} className={`${cls} border-line text-ink hover:border-brand hover:text-brand`}>
      {children}
    </Link>
  );
}
