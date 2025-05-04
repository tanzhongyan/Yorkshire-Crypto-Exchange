"use client";

import type React from "react";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LogIn, X, Home } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/components/AuthProvider";

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

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    identifier: "",
    password: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); // Clear any previous errors
    setIsLoading(true);

    try {
      // Call the login API endpoint
      const response = await fetch(
        "http://localhost:8000/api/v1/user/authenticate/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            identifier: formData.identifier,
            password: formData.password,
          }),
        },
      );

      // Parse the response
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("Invalid response format");
      }

      // Handle errors
      if (!response.ok) {
        if (data.error) {
          const detailsMessage = data.details ? `: ${data.details}` : "";
          throw new Error(`${data.error}${detailsMessage}`);
        } else {
          throw new Error("Failed to authenticate");
        }
      }

      // Login successful
      if (data.token) {
        // Set token in AuthProvider (which sets the cookie)
        login(data.token);

        // Redirect to dashboard
        router.push("/dashboard");
      } else {
        throw new Error("Authentication successful but no token received");
      }
    } catch (error: unknown) {
      // Handle different types of errors
      if (
        error instanceof Error &&
        error.name === "TypeError" &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Unable to connect to the server. Please check your internet connection or try again later.",
        );
      } else if (error instanceof Error && error.name === "SyntaxError") {
        setError("Received an invalid response from the server.");
      } else {
        setError(error instanceof Error ? error.message : "An error occurred");
      }
      console.error("Login error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="absolute top-6 left-6">
        <Link href="/" passHref>
          <Button variant="outline" className="text-sm">
            <Home className="h-4 w-4" />
            Back to Home
          </Button>
        </Link>
      </div>
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Sign in to your account
          </CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access your account
          </CardDescription>
        </CardHeader>
        {error && (
          <div className="px-6 pb-2">
            <Alert variant="destructive" className="flex flex-col gap-2 p-4">
              <div className="flex justify-between items-center">
                <AlertTitle>Error</AlertTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => setError("")}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <AlertDescription className="text-sm leading-relaxed">
                {error}
              </AlertDescription>
            </Alert>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="identifier">Username or Email</Label>
              <Input
                id="identifier"
                name="identifier"
                placeholder="Enter your username or email"
                required
                value={formData.identifier}
                onChange={handleChange}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href="/forgot-password"
                  className="text-sm text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                "Signing in..."
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In
                </>
              )}
            </Button>
            <p className="mt-4 text-center text-sm">
              Don&apos;t have an account?{" "}
              <Link href="/signup" className="text-primary hover:underline">
                Sign up
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
