"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const { login } = useAuth();

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		const success = login(password);
		if (!success) {
			setError("Incorrect password");
			setPassword("");
		}
	};

	return (
		<div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
			<div className="max-w-md w-full">
				<div className="bg-white rounded-lg shadow-lg p-8">
					<h1 className="text-3xl font-bold text-gray-800 mb-2 text-center">
						Roz
					</h1>
					<p className="text-gray-600 text-center mb-8">
						Enter password to access heatmap viewer
					</p>

					<form onSubmit={handleSubmit} className="space-y-4">
						<div>
							<label
								htmlFor="password"
								className="block text-sm font-medium text-gray-700 mb-2"
							>
								Password
							</label>
							<input
								id="password"
								type="password"
								value={password}
								onChange={(e) => {
									setPassword(e.target.value);
									setError("");
								}}
								className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
								placeholder="Enter password"
								autoFocus
							/>
						</div>

						{error && <div className="text-red-600 text-sm">{error}</div>}

						<button
							type="submit"
							className="w-full bg-blue-500 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-600 transition-colors"
						>
							Login
						</button>
					</form>
				</div>
			</div>
		</div>
	);
}
