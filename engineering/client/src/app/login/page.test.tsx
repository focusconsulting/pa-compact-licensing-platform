import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { useAuth } from "src/contexts/AuthContext";
import { expectNoAxeViolations } from "src/tests/axe";
import LoginPage from "./page";

const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));
vi.mock("src/contexts/AuthContext");

const mockSignIn = vi.fn();
const mockCompleteNewPassword = vi.fn();
const mockVerifyTotpSetup = vi.fn();
const mockAnswerTotp = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({
    signIn: mockSignIn,
    completeNewPassword: mockCompleteNewPassword,
    verifyTotpSetup: mockVerifyTotpSetup,
    answerTotp: mockAnswerTotp,
    signOut: vi.fn(),
    isLoading: false,
    idToken: null,
    email: null,
  } as ReturnType<typeof useAuth>);
});

describe("LoginPage", () => {
  it("renders the sign-in form", () => {
    render(<LoginPage />);
    expect(
      screen.getByRole("heading", { name: /Sign in/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Sign in/i }),
    ).toBeInTheDocument();
  });

  it("redirects to home after successful sign-in", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({ type: "success", session: {} });

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "password123");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows set-password form when newPasswordRequired", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: { phone_number: "+1234" },
    });

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "password");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: /Set a new password/i }),
      ).toBeInTheDocument(),
    );
  });

  it("shows error when sign-in fails", async () => {
    const user = userEvent.setup();
    mockSignIn.mockRejectedValue(new Error("Incorrect username or password"));

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "bad@example.com",
    );
    await user.type(document.getElementById("password")!, "wrongpass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/Incorrect username or password/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows error when new passwords do not match", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(
      screen.getByLabelText(/Confirm new password/),
      "DifferentPass!",
    );
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
  });

  it("redirects to home after successful password change", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });
    mockCompleteNewPassword.mockResolvedValue({ type: "success", session: {} });

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(
      screen.getByLabelText(/Confirm new password/),
      "NewPass123!",
    );
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows error when password change fails", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });
    mockCompleteNewPassword.mockRejectedValue(
      new Error("Password policy not met"),
    );

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(
      screen.getByLabelText(/Confirm new password/),
      "NewPass123!",
    );
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    await waitFor(() =>
      expect(screen.getByText(/Password policy not met/i)).toBeInTheDocument(),
    );
  });

  it("shows a generic error when sign-in fails with a non-Error value", async () => {
    const user = userEvent.setup();
    mockSignIn.mockRejectedValue("network down");

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "a@example.com",
    );
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() =>
      expect(screen.getByText("Sign in failed")).toBeInTheDocument(),
    );
  });

  it("shows a generic error when the password change fails with a non-Error value", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });
    mockCompleteNewPassword.mockRejectedValue("network down");

    render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "a@example.com",
    );
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));
    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(
      screen.getByLabelText(/Confirm new password/),
      "NewPass123!",
    );
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    await waitFor(() =>
      expect(screen.getByText("Password change failed")).toBeInTheDocument(),
    );
  });

  it("has no axe violations on the sign-in form", async () => {
    const { container } = render(<LoginPage />);
    await expectNoAxeViolations(container);
  });

  it("has no axe violations on the set-password form", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });

    const { container } = render(<LoginPage />);
    await user.type(
      screen.getByRole("textbox", { name: /Email address/i }),
      "test@example.com",
    );
    await user.type(document.getElementById("password")!, "password");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));
    await screen.findByRole("heading", { name: /Set a new password/i });

    await expectNoAxeViolations(container);
  });
  describe("TOTP", () => {
    const SECRET = "JBSWY3DPEHPK3PXP";

    async function signInTo(result: object) {
      const user = userEvent.setup();
      mockSignIn.mockResolvedValue(result);
      const view = render(<LoginPage />);
      await user.type(
        screen.getByRole("textbox", { name: /Email address/i }),
        "kim@example.com",
      );
      await user.type(document.getElementById("password")!, "password");
      await user.click(screen.getByRole("button", { name: /Sign in/i }));
      return { user, ...view };
    }

    async function enterCode(user: ReturnType<typeof userEvent.setup>) {
      await user.type(
        await screen.findByRole("textbox", { name: /Authentication code/i }),
        "123456",
      );
      await user.click(screen.getByRole("button", { name: /Continue/i }));
    }

    it("answers a TOTP challenge and goes to the dashboard", async () => {
      const cognitoUser = {};
      const { user } = await signInTo({
        type: "totpRequired",
        user: cognitoUser,
      });
      mockAnswerTotp.mockResolvedValue(undefined);

      await screen.findByRole("heading", {
        name: /Enter your authentication code/i,
      });
      await enterCode(user);

      await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
      expect(mockAnswerTotp).toHaveBeenCalledWith(cognitoUser, "123456");
    });

    it("shows the setup key and enrols with the first code", async () => {
      const cognitoUser = {};
      const { user } = await signInTo({
        type: "totpSetupRequired",
        user: cognitoUser,
        secret: SECRET,
      });
      mockVerifyTotpSetup.mockResolvedValue(undefined);

      await screen.findByRole("heading", {
        name: /Set up your authenticator app/i,
      });
      expect(
        screen.getByRole("img", {
          name: /QR code for your authenticator app/i,
        }),
      ).toBeInTheDocument();
      expect(screen.getByTestId("totp-secret")).toHaveTextContent(
        "JBSW Y3DP EHPK 3PXP",
      );
      expect(
        screen.getByRole("link", { name: /open it in your authenticator/i }),
      ).toHaveAttribute(
        "href",
        expect.stringMatching(
          /^otpauth:\/\/totp\/.*kim%40example\.com\?secret=JBSWY3DPEHPK3PXP/,
        ),
      );
      await enterCode(user);

      await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
      expect(mockVerifyTotpSetup).toHaveBeenCalledWith(cognitoUser, "123456");
    });

    it("asks a new user to enrol after setting a password", async () => {
      const { user } = await signInTo({
        type: "newPasswordRequired",
        user: {},
        userAttributes: {},
      });
      mockCompleteNewPassword.mockResolvedValue({
        type: "totpSetupRequired",
        user: {},
        secret: SECRET,
      });

      await user.type(
        await screen.findByLabelText(/New password/),
        "NewPass123!",
      );
      await user.type(
        screen.getByLabelText(/Confirm new password/),
        "NewPass123!",
      );
      await user.click(screen.getByRole("button", { name: /Set password/i }));

      expect(
        await screen.findByRole("heading", {
          name: /Set up your authenticator app/i,
        }),
      ).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("shows the error when a code is rejected", async () => {
      const { user } = await signInTo({ type: "totpRequired", user: {} });
      mockAnswerTotp.mockRejectedValue(new Error("Invalid code received"));

      await enterCode(user);

      expect(
        await screen.findByText(/Invalid code received/i),
      ).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("shows a generic error when a code fails with a non-Error value", async () => {
      const { user } = await signInTo({ type: "totpRequired", user: {} });
      mockAnswerTotp.mockRejectedValue("network down");

      await enterCode(user);

      expect(await screen.findByText("Code not accepted")).toBeInTheDocument();
    });

    it("has no axe violations on the setup step", async () => {
      const { container } = await signInTo({
        type: "totpSetupRequired",
        user: {},
        secret: SECRET,
      });
      await screen.findByRole("heading", {
        name: /Set up your authenticator app/i,
      });

      await expectNoAxeViolations(container);
    });
  });
});

describe("LoginPage, in a build that sets the local password", () => {
  /** The page as that build compiles it: the list is decided when the module loads. */
  async function renderDevPage() {
    vi.stubEnv("NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD", "Local-Passw0rd!");
    vi.resetModules();
    vi.doMock("src/lib/devSignIns", () => ({
      listMockUsers: () => Promise.resolve(["avery.active@demo.example"]),
    }));
    const auth = await import("src/contexts/AuthContext");
    vi.mocked(auth.useAuth).mockReturnValue({
      signIn: mockSignIn,
      completeNewPassword: mockCompleteNewPassword,
      verifyTotpSetup: mockVerifyTotpSetup,
      answerTotp: mockAnswerTotp,
      signOut: vi.fn(),
      isLoading: false,
      idToken: null,
      email: null,
    } as ReturnType<typeof useAuth>);
    const { default: DevLoginPage } = await import("./page");
    const view = render(<DevLoginPage />);
    vi.unstubAllEnvs();
    return view;
  }

  it("signs in as a seeded user in one click, showing what it tried", async () => {
    mockSignIn.mockResolvedValue({ type: "success", session: {} });
    await renderDevPage();

    await userEvent.click(
      await screen.findByRole("button", { name: "avery.active@demo.example" }),
    );

    expect(mockSignIn).toHaveBeenCalledWith(
      "avery.active@demo.example",
      "Local-Passw0rd!",
    );
    expect(screen.getByRole("textbox", { name: /Email address/i })).toHaveValue(
      "avery.active@demo.example",
    );
    expect(document.getElementById("password")).toHaveValue("Local-Passw0rd!");
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
  });
});

describe("LoginPage, in a build for a deployed environment", () => {
  it("has no list of seeded users", () => {
    render(<LoginPage />);

    expect(screen.queryByText("Seeded users")).toBeNull();
  });
});
