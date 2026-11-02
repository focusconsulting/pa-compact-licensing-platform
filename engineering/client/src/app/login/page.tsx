"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CognitoUser } from "amazon-cognito-identity-js";
import {
  Alert,
  AlertHeading,
  AlertText,
  Button,
  Form,
  Label,
  TextInput,
} from "@trussworks/react-uswds";
import { useAuth } from "src/contexts/AuthContext";

/**
 * Sign-in page. Signs in with Cognito (SRP); an admin-created user is asked to
 * choose a new password before continuing to the dashboard.
 */
export default function LoginPage() {
  const { signIn, completeNewPassword } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [pendingChallenge, setPendingChallenge] = useState<{
    user: CognitoUser;
    userAttributes: Record<string, string>;
  } | null>(null);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await signIn(email, password);
      if (result.type === "newPasswordRequired") {
        setPendingChallenge({
          user: result.user,
          userAttributes: result.userAttributes,
        });
      } else {
        router.push("/");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  async function handleNewPassword(
    e: React.FormEvent,
    challenge: { user: CognitoUser; userAttributes: Record<string, string> },
  ) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await completeNewPassword(
        challenge.user,
        newPassword,
        challenge.userAttributes,
      );
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Password change failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (pendingChallenge) {
    return (
      <div className="usa-section">
        <div className="grid-container">
          <h1>Set a new password</h1>
          <p>You must set a new password before continuing.</p>
          {error && (
            <Alert type="error" slim>
              <AlertHeading level="h2">Error</AlertHeading>
              <AlertText>{error}</AlertText>
            </Alert>
          )}
          <Form onSubmit={(e) => handleNewPassword(e, pendingChallenge)}>
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
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Set password"}
            </Button>
          </Form>
        </div>
      </div>
    );
  }

  return (
    <div className="usa-section">
      <div className="grid-container">
        <h1>Sign in</h1>
        {error && (
          <Alert type="error" slim>
            <AlertHeading level="h2">Error</AlertHeading>
            <AlertText>{error}</AlertText>
          </Alert>
        )}
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
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </Form>
      </div>
    </div>
  );
}
