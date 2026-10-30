import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";

import type { CognitoUserSession } from "amazon-cognito-identity-js";

import { useAuth } from "src/contexts/AuthContext";
import { getCurrentSession } from "src/lib/auth";
import { CurrentUserProvider, useCurrentUser } from "./CurrentUserContext";

vi.mock("src/lib/auth");
vi.mock("src/contexts/AuthContext");

const me = {
  user_id: "8f14e45f-ceea-467f-a0e6-2b5c3d1a9e2b",
  email: "pat@example.com",
  given_name: "Pat",
  family_name: "Morgan",
  role: "state_staff",
  state_code: "KS",
  is_active: true,
  permissions: ["read_general"],
};

function signedIn(idToken: string | null) {
  vi.mocked(useAuth).mockReturnValue({
    isLoading: false,
    idToken,
    email: idToken && "pat@example.com",
    signOut: vi.fn(),
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
  });
}

function Probe() {
  const { user, error } = useCurrentUser();
  return <p>{user?.email ?? error ?? "nobody"}</p>;
}

function renderProvider() {
  return render(
    <CurrentUserProvider>
      <Probe />
    </CurrentUserProvider>,
  );
}

/** Holds `/api/me` open until the test answers or fails it. */
function holdFetch() {
  let answer!: (response: Response) => void;
  let fail!: (reason: unknown) => void;
  vi.mocked(globalThis.fetch).mockImplementation(
    () =>
      new Promise<Response>((resolve, reject) => {
        answer = resolve;
        fail = reject;
      }),
  );
  const sent = () => waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
  return {
    answer: async (body: unknown) => {
      await sent();
      answer(Response.json(body));
    },
    fail: async (reason: unknown) => {
      await sent();
      fail(reason);
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "token" }),
  } as CognitoUserSession);
});

describe("CurrentUserProvider", () => {
  it("loads the signed-in user", async () => {
    signedIn("token");
    const request = holdFetch();

    renderProvider();
    await act(() => request.answer({ data: me }));

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
  });

  it("asks for nobody while signed out", () => {
    signedIn(null);

    renderProvider();

    expect(screen.getByText("nobody")).toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("drops a user who arrives after signing out", async () => {
    signedIn("token");
    const request = holdFetch();
    const { rerender } = renderProvider();

    signedIn(null);
    rerender(
      <CurrentUserProvider>
        <Probe />
      </CurrentUserProvider>,
    );
    await act(() => request.answer({ data: me }));

    expect(screen.getByText("nobody")).toBeInTheDocument();
  });

  it("drops an error that arrives after signing out", async () => {
    signedIn("token");
    const request = holdFetch();
    const { unmount } = renderProvider();

    unmount();
    await act(() => request.fail(new Error("offline")));

    expect(screen.queryByText("offline")).not.toBeInTheDocument();
  });
});
