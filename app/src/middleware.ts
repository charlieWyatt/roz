import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
	const authCookie = request.cookies.get("roz_auth");
	const isAuthenticated = authCookie?.value === "true";
	const isLoginPage = request.nextUrl.pathname === "/";
	const isDashboard = request.nextUrl.pathname.startsWith("/dashboard");

	// If trying to access dashboard without auth, redirect to login
	if (isDashboard && !isAuthenticated) {
		return NextResponse.redirect(new URL("/", request.url));
	}

	// If authenticated and trying to access login, redirect to dashboard
	if (isLoginPage && isAuthenticated) {
		return NextResponse.redirect(new URL("/dashboard", request.url));
	}

	return NextResponse.next();
}

export const config = {
	matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
