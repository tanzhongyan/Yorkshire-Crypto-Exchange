"use client";

import type React from "react";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, UserPlus, X, Home } from "lucide-react";
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
import { setCookie, getCookie } from "@/lib/cookies";

export default function SignupPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    username: "",
    fullname: "",
    phone: "",
    email: "",
    password: "",
    streetNumber: "",
    streetName: "",
    unitNumber: "",
    buildingName: "",
    district: "",
    city: "",
    stateProvince: "",
    postalCode: "",
    country: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); // Clear any previous errors
    setIsLoading(true);

    try {
      // 1. First get the token (BEFORE making the fetch call)
      const token = getCookie("jwt_token");

      // 2. Payload preparation remains the same
      const payload = {
        username: formData.username,
        fullname: formData.fullname,
        phone: formData.phone,
        email: formData.email,
        password: formData.password,
      };

      // 3. Call the API endpoint
      const response = await fetch(
        "http://localhost:8000/api/v1/identity/create-account",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token && { Authorization: `Bearer ${token}` }),
          },
          body: JSON.stringify(payload),
        },
      );

      // 4. Try to parse the response as JSON
      let data;
      try {
        data = await response.json();
      } catch {
        // If we can't parse JSON, use a default error structure
        data = { error: "Invalid response format" };
      }

      // 5. Handle errors if response is not ok
      if (!response.ok) {
        // Format error according to Swagger ErrorResponse schema
        if (data.error) {
          const detailsMessage = data.details?.message
            ? `: ${data.details.message}`
            : "";
          throw new Error(`${data.error}${detailsMessage}`);
        } else {
          throw new Error("Failed to create account");
        }
      }

      // 6. Account created successfully
      const userId = data.userId;
      if (!userId) {
        throw new Error("User ID not returned from server");
      }

      // 7. Store the userId in cookie
      setCookie("userId", userId, 3600); // 1 hour expiry

      // 8. Store JWT token if it's in the response
      if (data.token) {
        // Let the AuthProvider handle token storage
        login(data.token); // Pass only the token
        // No need to set userId again as we did it above
      }

      // 9. Redirect to dashboard page
      router.push("/dashboard");
    } catch (error: unknown) {
      // Handle different types of errors
      if (error instanceof Error && error.name === "TypeError" && error.message === "Failed to fetch") {
        setError(
          "Unable to connect to the server. Please check your internet connection or try again later.",
        );
      } else if (error instanceof Error && error.name === "SyntaxError") {
        setError("Received an invalid response from the server.");
      } else {
        if (error instanceof Error) {
          setError(error.message || "An error occurred");
        } else {
          setError("An error occurred");
        }
        console.error("Error creating account:", error);
      }
      console.error("Error creating account:", error);
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
      <Card className="w-full max-w-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Create an account
          </CardTitle>
          <CardDescription className="text-center">
            {"Enter your personal information"}
          </CardDescription>
        </CardHeader>
        {error && (
          <div className="px-6 pb-2">
            {" "}
            {/* match card padding */}
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
        <form onSubmit={handleSubmit} autoComplete="on">
          <CardContent>
            {
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    placeholder="Enter username"
                    required
                    value={formData.username}
                    onChange={handleChange}
                    autoComplete="username"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fullname">Full Name</Label>
                  <Input
                    id="fullname"
                    name="fullname"
                    placeholder="Enter your full name"
                    required
                    value={formData.fullname}
                    onChange={handleChange}
                    autoComplete="name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Enter your email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    autoComplete="email"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    name="phone"
                    placeholder="Enter your phone number"
                    required
                    value={formData.phone}
                    onChange={handleChange}
                    autoComplete="phone"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Create a password"
                      required
                      value={formData.password}
                      onChange={handleChange}
                      autoComplete="password"
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
              </div>
            }
          </CardContent>
          <CardFooter className="flex flex-col">
            {
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  "Creating Account..."
                ) : (
                  <>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Create Account
                  </>
                )}
              </Button>
            }
            <p className="mt-4 text-center text-sm">
              Already have an account?{" "}
              <Link href="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
