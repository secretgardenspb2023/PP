import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "О проекте — PoiskPlant",
  description:
    "PoiskPlant — электронный справочник растений: характеристики, уход и использование в дизайне сада для тысяч видов.",
};

export default function AboutPage() {
  return (
    <div className="container-page py-12">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-[32px] font-bold text-ink">О проекте</h1>

        <div className="space-y-4 rounded-card border border-line bg-white p-6 text-[16px] leading-relaxed text-accent-ink shadow-soft">
          <p>
            <span className="font-semibold text-ink">PoiskPlant</span> — электронный
            справочник растений. Здесь собраны характеристики, особенности ухода и
            применение в ландшафтном дизайне для тысяч видов и сортов.
          </p>
          <p>
            Находите растения по названию (русскому или латинскому) или подбирайте по
            параметрам — освещению, почве, размерам, зимостойкости и другим
            характеристикам.
          </p>
          <p className="text-[15px] text-muted">
            Полный текст раздела готовится и будет дополнен.
          </p>
        </div>
      </div>
    </div>
  );
}
