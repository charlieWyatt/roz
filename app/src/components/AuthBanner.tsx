"use client";

import { useAuth } from "@/hooks/useAuth";

export function AuthBanner() {
	const { logout } = useAuth();

	return (
		<div className="bg-white border-b border-gray-200 px-6 py-3 flex justify-between items-center">
			<div className="text-xl font-bold text-gray-800">Roz</div>
			<button
				onClick={logout}
				className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
			>
				Logout
			</button>
		</div>
	);
}
