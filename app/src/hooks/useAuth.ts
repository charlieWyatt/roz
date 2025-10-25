"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
	isAuthenticated,
	clearAuthCookie,
	setAuthCookie,
	verifyPassword,
} from "@/lib/auth";

export function useAuth() {
	const [authenticated, setAuthenticated] = useState(false);
	const [loading, setLoading] = useState(true);
	const router = useRouter();

	useEffect(() => {
		setAuthenticated(isAuthenticated());
		setLoading(false);
	}, []);

	const login = (password: string): boolean => {
		if (verifyPassword(password)) {
			setAuthCookie();
			setAuthenticated(true);
			router.push("/dashboard");
			return true;
		}
		return false;
	};

	const logout = () => {
		clearAuthCookie();
		setAuthenticated(false);
		router.push("/");
	};

	return {
		authenticated,
		loading,
		login,
		logout,
	};
}
