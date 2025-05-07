"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
const API_GATEWAY_URL = process.env.API_GATEWAY_URL;

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    setSuccess(false);

    try {
      await fetch(
        `${API_GATEWAY_URL}/api/v1/user/authenticate/reset-password-request`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email: email.toLowerCase() }),
        },
      );

      // Always show success message regardless of email existing or not
      setSuccess(true);
      setEmail("");

      // Optionally, you can log response if needed for dev
      // const data = await response.json()
      // console.log(data)
    } catch (error: unknown) {
      setError(
        error instanceof Error ? error.message : "An error occurred"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Reset your password
          </CardTitle>
          <CardDescription className="text-center">
            Enter your email address and we&apos;ll send you a link to reset
            your password
          </CardDescription>
        </CardHeader>

        {error && (
          <div className="px-6 pb-2">
            <Alert variant="destructive">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </div>
        )}

        {success ? (
          <>
            <CardContent className="space-y-4">
              <Alert>
                <Mail className="h-4 w-4" />
                <AlertTitle>Check your email</AlertTitle>
                <AlertDescription>
                  We&apos;ve sent you a password reset link. Please check your
                  email and follow the instructions.
                </AlertDescription>
              </Alert>
            </CardContent>
            <CardFooter className="flex flex-col">
              <div className="text-center">
                <Link
                  href="/login"
                  className="text-primary hover:underline inline-flex items-center"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to login
                </Link>
              </div>
            </CardFooter>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Sending..." : "Send reset link"}
              </Button>
              <div className="mt-4 text-center">
                <Link
                  href="/login"
                  className="text-primary hover:underline inline-flex items-center"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to login
                </Link>
              </div>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  );
}
