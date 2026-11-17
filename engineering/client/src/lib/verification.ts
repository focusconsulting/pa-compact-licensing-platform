import type { components } from "src/api/schema";
import { publicApi } from "src/lib/api";

export type HolderSummary = components["schemas"]["PrivilegeHolderSummary"];
export type Holder = components["schemas"]["PrivilegeHolder"];
export type ResultsPage = components["schemas"]["Page"];

/** The two searches public verification takes, and no others (FLOW-08). */
export type Search =
  { first_name: string; last_name: string } | { privilege_number: string };

/** A failed lookup, by HTTP status: 429 is the web firewall's rate limit, 404 a PA who isn't listed. */
export class VerificationError extends Error {
  constructor(readonly status: number) {
    super(String(status));
  }
}

/** One page of the PAs who hold a privilege and match the search in full. */
export async function searchHolders(search: Search, page: number) {
  const { data, response } = await publicApi.GET(
    "/api/public/privilege-holders",
    { params: { query: { ...search, page } } },
  );
  if (!data) throw new VerificationError(response.status);
  return data;
}

/** One PA's public record: their name, state of qualifying license, and privileges. */
export async function loadHolder(id: string): Promise<Holder> {
  const { data, response } = await publicApi.GET(
    "/api/public/privilege-holders/{holder_id}",
    { params: { path: { holder_id: id } } },
  );
  if (!data) throw new VerificationError(response.status);
  return data.data;
}

type Params = Pick<URLSearchParams, "get">;

/** The search a page address carries, or none when it carries neither whole search. */
export function searchFrom(params: Params): Search | null {
  const number = params.get("privilege_number");
  const first = params.get("first_name");
  const last = params.get("last_name");
  if (number) return { privilege_number: number };
  if (first && last) return { first_name: first, last_name: last };
  return null;
}

/** The page of results an address asks for; anything that isn't a page number is the first. */
export function pageFrom(params: Params): number {
  const page = Number(params.get("page"));
  return Number.isInteger(page) && page > 0 ? page : 1;
}

/** A search as a query string, so results and a PA's page can be linked to, reloaded, and gone back to. */
export function searchQuery(search: Search, page = 1): string {
  const query = new URLSearchParams(search);
  if (page > 1) query.set("page", String(page));
  return query.toString();
}

/** A PA's name as public verification shows it; the suffix tells apart two PAs who share one. */
export function fullName(
  holder: Pick<Holder, "first_name" | "last_name" | "name_suffix">,
): string {
  return [holder.first_name, holder.last_name, holder.name_suffix]
    .filter(Boolean)
    .join(" ");
}
