import Link from "next/link";
import { CookieSettingsLink } from "@/components/CookieSettingsLink";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-line bg-surface">
      <div className="container-page flex flex-col gap-4 py-8 text-[14px] text-muted sm:flex-row sm:items-center sm:justify-between">
        <p>© {new Date().getFullYear()} PoiskPlant — электронный справочник растений</p>
        <nav className="flex flex-wrap gap-x-5 gap-y-2">
          <Link href="/catalog" className="hover:text-brand">Каталог</Link>
          <Link href="/about" className="hover:text-brand">О проекте</Link>
          <Link href="/contacts" className="hover:text-brand">Контакты</Link>
          <Link href="/privacy" className="hover:text-brand">Политика cookie</Link>
          <CookieSettingsLink />
        </nav>
      </div>
    </footer>
  );
}
