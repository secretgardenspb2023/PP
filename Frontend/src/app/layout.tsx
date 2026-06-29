import type { Metadata } from "next";
import { Rubik, Noto_Sans } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { YandexMetrika } from "@/components/YandexMetrika";
import { CookieConsent } from "@/components/CookieConsent";

// Headings (Figma: Rubik 700). Body (Figma: Noto Sans 400/500/600).
// cyrillic subset is required — the catalog is Russian.
const rubik = Rubik({
  subsets: ["latin", "cyrillic"],
  variable: "--font-rubik",
  display: "swap",
});

const notoSans = Noto_Sans({
  subsets: ["latin", "cyrillic"],
  variable: "--font-noto",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PoiskPlant — электронный справочник растений",
  description:
    "Каталог из 12 000+ растений: поиск по названию, фасетные фильтры, карточки с характеристиками, уходом и дизайном.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ru"
      className={`${rubik.variable} ${notoSans.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-white text-ink">
        <AuthProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </AuthProvider>
        <YandexMetrika />
        <CookieConsent />
      </body>
    </html>
  );
}
