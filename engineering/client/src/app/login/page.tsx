"use client";

import { Suspense, lazy, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  AlertHeading,
  AlertText,
  Button,
  Form,
  Label,
  TextInput,
} from "@trussworks/react-uswds";
import { QRCodeSVG } from "qrcode.react";
import { useAuth } from "src/contexts/AuthContext";
import { SignInResult, totpUri } from "src/lib/auth";

// The local Cognito mock's shared password. A build for a deployed environment
// leaves it empty, which compiles the list and its module out (ADR-0020).
const DEV_PASSWORD = process.env.NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD;
const DevSignIns = process.env.NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD
  ? lazy(() => import("src/components/DevSignIns"))
  : null;

type Challenge = Exclude<SignInResult, { type: "success" }>;
type TotpChallenge = Extract<
  Challenge,
  { type: "totpSetupRequired" | "totpRequired" }
>;

function ErrorAlert({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <Alert type="error" slim className="margin-bottom-3">
      <AlertHeading level="h2">Error</AlertHeading>
      <AlertText>{error}</AlertText>
    </Alert>
  );
}

/**
 * Sign-in page. Signs in with Cognito (SRP), then answers each challenge
 * Cognito sets: an admin-created user chooses a new password, a user without
 * an authenticator app enrols one, and every sign-in ends with a TOTP code.
 */
export default function LoginPage() {
  const { signIn, completeNewPassword, verifyTotpSetup, answerTotp } =
    useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [challenge, setChallenge] = useState<Challenge | null>(null);

  function proceed(result: SignInResult) {
    if (result.type === "success") {
      router.push("/dashboard");
    } else {
      setChallenge(result);
    }
  }

  async function submit(action: () => Promise<void>, fallbackError: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      await action();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : fallbackError);
    } finally {
      setIsSubmitting(false);
    }
  }

  const signInWith = (as: string, withPassword: string) =>
    submit(
      async () => proceed(await signIn(as, withPassword)),
      "Sign in failed",
    );

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    return signInWith(email, password);
  };

  // Fills the form as well as submitting, so a failure leaves what was tried.
  const signInAs = (seeded: string) => {
    setEmail(seeded);
    setPassword(DEV_PASSWORD as string);
    void signInWith(seeded, DEV_PASSWORD as string);
  };

  function handleNewPassword(
    e: React.FormEvent,
    pending: Extract<Challenge, { type: "newPasswordRequired" }>,
  ) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return undefined;
    }
    return submit(
      async () =>
        proceed(
          await completeNewPassword(
            pending.user,
            newPassword,
            pending.userAttributes,
          ),
        ),
      "Password change failed",
    );
  }

  function handleCode(e: React.FormEvent, pending: TotpChallenge) {
    e.preventDefault();
    return submit(async () => {
      if (pending.type === "totpSetupRequired") {
        await verifyTotpSetup(pending.user, code);
      } else {
        await answerTotp(pending.user, code);
      }
      router.push("/dashboard");
    }, "Code not accepted");
  }

  if (challenge?.type === "newPasswordRequired") {
    return (
      <div className="usa-section">
        <div className="grid-container">
          <div className="grid-row">
            <div className="grid-col-12 tablet:grid-col-8 desktop:grid-col-6">
              <h1 className="margin-top-0 margin-bottom-2">
                Set a new password
              </h1>
              <p>You must set a new password before continuing.</p>
              <ErrorAlert error={error} />
              <Form onSubmit={(e) => handleNewPassword(e, challenge)}>
                <Label htmlFor="new-password">New password</Label>
                <TextInput
                  id="new-password"
                  name="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
                <Label htmlFor="confirm-password">Confirm new password</Label>
                <TextInput
                  id="confirm-password"
                  name="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <Button
                  type="submit"
                  className="margin-top-3"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Saving…" : "Set password"}
                </Button>
              </Form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (challenge) {
    const setup = challenge.type === "totpSetupRequired";
    return (
      <div className="usa-section">
        <div className="grid-container">
          <div className="grid-row">
            <div className="grid-col-12 tablet:grid-col-8 desktop:grid-col-6">
              <h1 className="margin-top-0 margin-bottom-2">
                {setup
                  ? "Set up your authenticator app"
                  : "Enter your authentication code"}
              </h1>
              {setup ? (
                <>
                  <p>
                    Scan this QR code with an authenticator app, such as Google
                    Authenticator or Microsoft Authenticator.
                  </p>
                  <QRCodeSVG
                    value={totpUri(email, challenge.secret)}
                    title="QR code for your authenticator app"
                    role="img"
                    marginSize={4}
                  />
                  <p>
                    On this device,{" "}
                    <a href={totpUri(email, challenge.secret)}>
                      open it in your authenticator app
                    </a>
                    ; or enter this setup key:
                  </p>
                  <p>
                    <code data-testid="totp-secret">
                      {challenge.secret.match(/.{1,4}/g)?.join(" ")}
                    </code>
                  </p>
                  <p>Then enter the 6-digit code the app shows.</p>
                </>
              ) : (
                <p>Enter the 6-digit code from your authenticator app.</p>
              )}
              <ErrorAlert error={error} />
              <Form onSubmit={(e) => handleCode(e, challenge)}>
                <Label htmlFor="totp-code">Authentication code</Label>
                <TextInput
                  id="totp-code"
                  name="totp-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
                <Button
                  type="submit"
                  className="margin-top-3"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Checking…" : "Continue"}
                </Button>
              </Form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="usa-section">
      <div className="grid-container">
        <div className="grid-row">
          <div className="grid-col-12 tablet:grid-col-8 desktop:grid-col-6">
            <h1 className="margin-top-0 margin-bottom-3">Sign in</h1>
            <ErrorAlert error={error} />
            <div className="bg-base-lightest padding-3 border border-base-lighter radius-md">
              <Form onSubmit={handleSignIn}>
                <Label htmlFor="email">Email address</Label>
                <TextInput
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Label htmlFor="password">Password</Label>
                <TextInput
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <Button
                  type="submit"
                  className="margin-top-3"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Signing in…" : "Sign in"}
                </Button>
              </Form>
            </div>
            {DevSignIns && (
              <Suspense>
                <DevSignIns onPick={signInAs} />
              </Suspense>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
