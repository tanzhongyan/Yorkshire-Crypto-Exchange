import { NextRequest, NextResponse } from "next/server";
import jwt from "jsonwebtoken";

const SECRET = "esdisfun"; // Must match your backend exactly

export async function middleware(request: NextRequest) {
  const token = request.cookies.get("jwt_token")?.value;
  console.log("===== MIDDLEWARE START =====");
  console.log("Cookie =>", token);

  // If no token, redirect (unless on login page)
  if (!token && !request.nextUrl.pathname.startsWith("/login")) {
    console.log("No token found, redirecting to /login");
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token) {
    try {
      const payload = jwt.verify(token, SECRET);
      console.log("JWT verified, payload =>", payload);
      // If verification passes, allow request
      console.log("===== MIDDLEWARE END (success) =====");
      return NextResponse.next();
    } catch (error) {
      console.log("JWT verification error =>", error);
      // If token is invalid, redirect
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  console.log("On login page or unprotected path => continuing");
  console.log("===== MIDDLEWARE END (no token needed) =====");
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/profile/:path*", "/api/protected/:path*"],
};
