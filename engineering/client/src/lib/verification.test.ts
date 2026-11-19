import { describe, expect, it } from "vitest";

import { answerFetch } from "src/tests/fetch";
import { HOLDER_ID, holder, summary } from "src/tests/verification";
import {
  VerificationError,
  fullName,
  loadHolder,
  pageFrom,
  searchFrom,
  searchHolders,
  searchQuery,
} from "./verification";

const params = (query: string) => new URLSearchParams(query);

describe("searchHolders", () => {
  it("asks for one page of a search, with no token", async () => {
    const fetchSpy = answerFetch({
      data: [summary()],
      page: { number: 2, size: 25, total: 26 },
    });

    const result = await searchHolders(
      { first_name: "Jordan", last_name: "Sample" },
      2,
    );

    const [request] = fetchSpy.mock.calls[0] as [Request];
    expect(request.url).toBe(
      "http://api.test/api/public/privilege-holders?first_name=Jordan&last_name=Sample&page=2",
    );
    expect(request.headers.has("Authorization")).toBe(false);
    expect(result.data[0].last_name).toBe("Sample");
    expect(result.page.total).toBe(26);
  });

  it("fails with the response's status", async () => {
    answerFetch({ code: "RATE_LIMITED", details: [] }, 429);

    await expect(
      searchHolders({ privilege_number: "PA-OK-000001" }, 1),
    ).rejects.toEqual(new VerificationError(429));
  });
});

describe("loadHolder", () => {
  it("returns the PA's public record", async () => {
    const fetchSpy = answerFetch({ data: holder() });

    const loaded = await loadHolder(HOLDER_ID);

    const [request] = fetchSpy.mock.calls[0] as [Request];
    expect(request.url).toBe(
      `http://api.test/api/public/privilege-holders/${HOLDER_ID}`,
    );
    expect(loaded.privileges).toHaveLength(3);
  });

  it("fails with the response's status", async () => {
    answerFetch({ code: "NOT_FOUND", details: [] }, 404);

    await expect(loadHolder(HOLDER_ID)).rejects.toMatchObject({ status: 404 });
  });
});

describe("searchFrom", () => {
  it.each([
    [
      "first_name=Jordan&last_name=Sample",
      { first_name: "Jordan", last_name: "Sample" },
    ],
    ["privilege_number=PA-OK-000001", { privilege_number: "PA-OK-000001" }],
    ["first_name=Jordan", null],
    ["last_name=Sample", null],
    ["", null],
  ])("reads %j as %j", (query, search) => {
    expect(searchFrom(params(query))).toEqual(search);
  });
});

describe("pageFrom", () => {
  it.each([
    ["page=3", 3],
    ["", 1],
    ["page=0", 1],
    ["page=1.5", 1],
    ["page=two", 1],
  ])("reads %j as page %i", (query, page) => {
    expect(pageFrom(params(query))).toBe(page);
  });
});

describe("searchQuery", () => {
  it("leaves the first page out of the address", () => {
    expect(searchQuery({ first_name: "Jordan", last_name: "Sample" })).toBe(
      "first_name=Jordan&last_name=Sample",
    );
  });

  it("carries a later page", () => {
    expect(searchQuery({ privilege_number: "PA-OK-000001" }, 2)).toBe(
      "privilege_number=PA-OK-000001&page=2",
    );
  });
});

describe("fullName", () => {
  it("ends with the suffix when the PA has one", () => {
    expect(fullName(summary({ name_suffix: "Jr." }))).toBe("Jordan Sample Jr.");
    expect(fullName(summary())).toBe("Jordan Sample");
  });
});
