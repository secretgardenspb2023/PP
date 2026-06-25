// Typed client for the PoiskPlant catalog API (Django/DRF, stage 5).
// Shapes mirror the live responses (see docs + serializers.py).

const SERVER_BASE = process.env.API_BASE ?? "http://localhost:8000/api/v1";
const BROWSER_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

// On the server use the internal base; in the browser use the public one.
const base = () => (typeof window === "undefined" ? SERVER_BASE : BROWSER_BASE);

export type PlantListItem = {
  id_plant: number;
  url_slug: string;
  name: string;
  name_rus: string;
  lat_name_unique: string;
  usda_zone: number | null;
  species: string;
  genus: string;
  family: string;
  main_photo: string | null;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type FacetValue = { value: string; count: number; label?: string };
export type Facets = Record<string, FacetValue[]>;

export type Synonym = {
  synonym_name: string;
  full_name: string | null;
  synonym_lang: string | null;
  synonym_type: string | null;
  is_binomial: boolean;
  level: "genus" | "species" | "plant";
};

export type PlantPhoto = {
  id: number;
  public_url: string | null;
  preview_url: string | null;
  is_main: boolean;
  source_type: string | null;
};

export type PlantDetail = {
  id_plant: number;
  url_slug: string;
  name: string;
  name_rus: string;
  lat_name_unique: string;
  variety: string | null;
  rus_name_unique: string | null;
  usda_zone: number | null;
  is_template: boolean;
  is_ishs_registered: boolean;
  created_at: string;
  taxonomy: {
    species: string | null;
    species_rus: string | null;
    genus: string | null;
    genus_rus: string | null;
    family_lat: string | null;
    family_rus: string | null;
  };
  characteristics: Record<string, unknown> & {
    height_max_cm?: number | null;
    diameter_max_cm?: number | null;
    annual_growth_cm?: number | null;
  };
  descriptions: {
    text?: string | null;
    facts?: string | null;
    requirements?: string | null;
    problems?: string | null;
    diseases_pests?: string | null;
    propagation?: string | null;
    usage?: string | null;
  };
  synonyms: Synonym[];
  photos: PlantPhoto[];
};

export type SearchHit = {
  id_plant: number;
  url_slug: string;
  name: string;
  lat_name: string;
  family: string;
  score: number;
  highlight: Record<string, string[]>;
};
export type SearchResponse = { count: number; results: SearchHit[]; engine: string };

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  // Server-side calls hit the backend over plain HTTP inside the Docker network;
  // tell Django the original request was HTTPS (SECURE_PROXY_SSL_HEADER) so its
  // SECURE_SSL_REDIRECT doesn't 302 us to https.
  const serverHeaders: Record<string, string> =
    typeof window === "undefined" ? { "X-Forwarded-Proto": "https" } : {};
  const res = await fetch(`${base()}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...serverHeaders },
  });
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function listPlants(
  params: Record<string, string | number | undefined> = {},
  init?: RequestInit,
): Promise<Paginated<PlantListItem>> {
  return getJSON(`/plants/${qs(params)}`, init);
}

export function getFacets(
  params: Record<string, string | number | undefined> = {},
  init?: RequestInit,
): Promise<Facets> {
  return getJSON(`/plants/facets/${qs(params)}`, init);
}

export function getPlant(idOrSlug: number | string, init?: RequestInit): Promise<PlantDetail> {
  // idOrSlug — числовой id или url_slug (ЧПУ). Кодируем для безопасных слагов
  // (кириллица/спецсимволы); бэкенд резолвит и по id, и по слагу.
  return getJSON(`/plants/${encodeURIComponent(String(idOrSlug))}/`, init);
}

export function search(
  q: string,
  page = 1,
  init?: RequestInit,
): Promise<SearchResponse> {
  return getJSON(`/search/${qs({ q, page })}`, init);
}

export type Suggestion = { id_plant: number; url_slug: string; name: string };

export function suggest(q: string, init?: RequestInit): Promise<Suggestion[]> {
  return getJSON(`/search/suggest/${qs({ q })}`, init);
}

export type Histogram = {
  min: number | null;
  max: number | null;
  buckets: { from: number; to: number; count: number }[];
};
export type Histograms = Record<string, Histogram>;

export function getHistograms(
  params: Record<string, string | number | undefined> = {},
  init?: RequestInit,
): Promise<Histograms> {
  return getJSON(`/plants/histograms/${qs(params)}`, init);
}
