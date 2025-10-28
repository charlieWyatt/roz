const SECRET_PASSWORD = "alwayswatching";
const AUTH_COOKIE_NAME = "roz_auth";

export function verifyPassword(password: string): boolean {
	return password === SECRET_PASSWORD;
}

export function setAuthCookie() {
	// Set cookie for 7 days
	const expires = new Date();
	expires.setDate(expires.getDate() + 7);
	document.cookie = `${AUTH_COOKIE_NAME}=true; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
}

export function clearAuthCookie() {
	document.cookie = `${AUTH_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

export function isAuthenticated(): boolean {
	if (typeof document === "undefined") return false;
	return document.cookie.includes(`${AUTH_COOKIE_NAME}=true`);
}
