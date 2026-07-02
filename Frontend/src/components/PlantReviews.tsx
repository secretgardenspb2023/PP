"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@/components/auth/AuthProvider";
import { createReview, getReviews, type Review } from "@/lib/api";

// Сжатие фото в браузере до лимита отзыва (1 МБ): даунскейл до maxDim по большей
// стороне + понижение JPEG-качества, пока не влезет. Так фото с телефона (2–5 МБ)
// не отклоняются, а ужимаются. GIF/уже-мелкие не трогаем. Бэкенд (Pillow нет) не задействуем.
async function compressImage(file: File, maxBytes: number, maxDim: number): Promise<File> {
  if (!file.type.startsWith("image/") || file.type === "image/gif") return file;
  if (file.size <= maxBytes) return file; // уже влезает
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((res, rej) => {
      const i = new Image();
      i.onload = () => res(i);
      i.onerror = () => rej(new Error("image load"));
      i.src = url;
    });
    const scale = Math.min(1, maxDim / Math.max(img.naturalWidth, img.naturalHeight));
    const w = Math.round(img.naturalWidth * scale);
    const h = Math.round(img.naturalHeight * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(img, 0, 0, w, h);
    let blob: Blob | null = null;
    let q = 0.85;
    for (let i = 0; i < 6; i++) {
      blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", q));
      if (!blob || blob.size <= maxBytes) break;
      q -= 0.13;
    }
    if (!blob || blob.size >= file.size) return file; // не помогло — оставляем оригинал
    return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file;
  } finally {
    URL.revokeObjectURL(url);
  }
}

const REVIEW_MAX = 1024 * 1024; // 1 МБ на фото (как на бэкенде)

export function PlantReviews({ plantId }: { plantId: number }) {
  const { user, token } = useAuth();
  const pathname = usePathname();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [count, setCount] = useState(0);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [lightbox, setLightbox] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // закрытие лайтбокса по Esc
  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);
  // превью выбранных фото (с очисткой object-URL, чтобы не текла память)
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  useEffect(() => {
    getReviews(plantId)
      .then((d) => {
        setReviews(d.results);
        setCount(d.count);
      })
      .catch(() => {});
  }, [plantId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await createReview(plantId, text.trim(), files, token);
      setMsg(res.detail || "Отзыв отправлен на модерацию.");
      setText("");
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Не удалось отправить отзыв.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-card border border-line bg-white p-6 shadow-soft">
      <h2 className="mb-4 text-[20px] font-semibold text-ink">
        Отзывы{count ? ` (${count})` : ""}
      </h2>

      {reviews.length === 0 ? (
        <p className="text-[15px] text-muted">Пока отзывов нет. Будьте первым!</p>
      ) : (
        <ul className="space-y-5">
          {reviews.map((r) => (
            <li key={r.id} className="border-b border-line pb-4 last:border-0 last:pb-0">
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink">{r.author_name || "Пользователь"}</span>
                <span className="text-[13px] text-muted">
                  {new Date(r.created_at).toLocaleDateString("ru-RU")}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-line text-[15px] leading-relaxed text-accent-ink">{r.text}</p>
              {r.photos.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {r.photos.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setLightbox(p.public_url)}
                      className="cursor-zoom-in"
                      aria-label="Открыть фото"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={p.preview_url || p.public_url}
                        alt="фото из отзыва"
                        className="size-20 rounded-control object-cover transition-transform hover:scale-[1.03]"
                      />
                    </button>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 border-t border-line pt-5">
        {!user ? (
          <p className="text-[15px] text-muted">
            <Link href={`/login?next=${encodeURIComponent(pathname)}`} className="font-medium text-brand hover:text-brand-dark">Войдите</Link>
            , чтобы оставить отзыв.
          </p>
        ) : msg ? (
          <p className="rounded-control bg-brand/10 px-4 py-2 text-[14px] text-brand-dark">{msg}</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-3">
            <h3 className="text-[16px] font-medium text-ink">Оставить отзыв</h3>
            {err && (
              <p className="rounded-control bg-[#fdecec] px-4 py-2 text-[14px] text-danger">{err}</p>
            )}
            <textarea
              required
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              className="auth-input"
              placeholder="Ваш отзыв о растении…"
            />
            <input
              ref={fileRef}
              id="review-photos"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              onChange={async (e) => {
                // Крупные фото сжимаем в браузере до ~1 МБ (не отклоняем). До 5 фото.
                const all = Array.from(e.target.files ?? []).slice(0, 5);
                setErr(null);
                const out: File[] = [];
                for (const f of all) out.push(await compressImage(f, Math.floor(REVIEW_MAX * 0.93), 1600));
                const fit = out.filter((f) => f.size <= REVIEW_MAX);
                if (fit.length < out.length) {
                  setErr("Некоторые фото не удалось сжать до 1 МБ — уменьшите размер и попробуйте снова.");
                }
                setFiles(fit);
              }}
              className="hidden"
            />
            <label
              htmlFor="review-photos"
              className="inline-flex cursor-pointer items-center gap-2 rounded-control border-2 border-dashed border-brand/50 bg-brand/5 px-4 py-2.5 text-[14px] font-medium text-brand-dark transition-colors hover:border-brand hover:bg-brand/10"
            >
              📷 Прикрепить фото{files.length ? ` (${files.length})` : ""}
            </label>
            {previews.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {previews.map((u, i) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={i}
                    src={u}
                    alt={files[i]?.name}
                    className="size-16 rounded-control border border-line object-cover"
                  />
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setFiles([]);
                    if (fileRef.current) fileRef.current.value = "";
                  }}
                  className="self-center text-[13px] text-danger hover:underline"
                >
                  очистить
                </button>
              </div>
            )}
            <p className="text-[13px] text-muted">
              До 5 фото. Крупные снимки автоматически сжимаются до 1 МБ. Форматы: JPG, PNG, WebP, GIF.
              {!user?.is_staff && " Отзыв появится после проверки модератором."}
            </p>
            <button
              type="submit"
              disabled={busy || text.trim().length < 3}
              className="h-10 rounded-control bg-brand px-5 font-medium text-white transition-colors hover:bg-brand-light hover:text-brand-dark disabled:opacity-60"
            >
              {busy ? "Отправляем…" : "Отправить отзыв"}
            </button>
          </form>
        )}
      </div>

      {lightbox && typeof document !== "undefined" &&
        createPortal(
          <div
            onClick={() => setLightbox(null)}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4"
            role="dialog"
            aria-modal="true"
          >
            <button
              type="button"
              onClick={() => setLightbox(null)}
              className="absolute right-5 top-3 text-4xl leading-none text-white/90 hover:text-white"
              aria-label="Закрыть"
            >
              ×
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={lightbox}
              alt="фото отзыва"
              onClick={(e) => e.stopPropagation()}
              className="max-h-[90vh] max-w-[90vw] rounded-card object-contain"
            />
          </div>,
          document.body,
        )}
    </section>
  );
}
