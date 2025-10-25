"use client";

import { useState, useEffect } from "react";
import { DayPicker } from "react-day-picker";
import { format } from "date-fns";
import "react-day-picker/dist/style.css";

interface Camera {
	camera_id: string;
	total_minutes: number;
	latest_activity: string;
	earliest_activity: string;
}

export default function Home() {
	const [cameras, setCameras] = useState<Camera[]>([]);
	const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
	const [selectedDate, setSelectedDate] = useState<Date | undefined>();
	const [heatmapUrl, setHeatmapUrl] = useState<string | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	// Fetch cameras on mount
	useEffect(() => {
		fetch("/api/cameras")
			.then((res) => res.json())
			.then((data) => {
				const cameraList = data.cameras || [];
				setCameras(cameraList);
				if (cameraList.length > 0) {
					setSelectedCamera(cameraList[0].camera_id);
				}
			})
			.catch((err) => {
				console.error("Failed to fetch cameras:", err);
				setCameras([]);
			});
	}, []);

	// Fetch heatmap when date selected
	useEffect(() => {
		if (!selectedCamera || !selectedDate) {
			setHeatmapUrl(null);
			return;
		}

		setLoading(true);
		setError(null);

		const dateStr = format(selectedDate, "yyyy-MM-dd");
		const url = `/api/heatmap/image?camera_id=${selectedCamera}&date=${dateStr}`;

		fetch(url)
			.then((res) => {
				if (!res.ok) throw new Error("No data for this date");
				setHeatmapUrl(url);
				setLoading(false);
			})
			.catch((err) => {
				setError(err.message);
				setHeatmapUrl(null);
				setLoading(false);
			});
	}, [selectedCamera, selectedDate]);

	return (
		<div className="flex h-screen bg-gray-50">
			{/* Sidebar */}
			<div className="w-64 bg-white border-r border-gray-200 p-6">
				<h2 className="text-xl font-bold mb-4 text-gray-800">Cameras</h2>
				<div className="space-y-2">
					{cameras?.map((camera) => (
						<button
							key={camera.camera_id}
							onClick={() => {
								setSelectedCamera(camera.camera_id);
								setSelectedDate(undefined);
							}}
							className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
								selectedCamera === camera.camera_id
									? "bg-blue-500 text-white"
									: "bg-gray-100 text-gray-700 hover:bg-gray-200"
							}`}
						>
							<div className="font-medium">{camera.camera_id}</div>
							<div className="text-sm opacity-75">
								{camera.total_minutes} minutes
							</div>
						</button>
					))}
				</div>

				{(!cameras || cameras.length === 0) && (
					<div className="text-gray-500 text-sm">
						{cameras === undefined ? "Loading..." : "No cameras found"}
					</div>
				)}
			</div>

			{/* Main content */}
			<div className="flex-1 p-8">
				{selectedCamera ? (
					<div className="max-w-6xl mx-auto">
						<h1 className="text-3xl font-bold mb-2 text-gray-800">
							{selectedCamera}
						</h1>
						<p className="text-gray-600 mb-8">Select a date to view heatmap</p>

						<div className="flex gap-8">
							{/* Calendar */}
							<div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
								<DayPicker
									mode="single"
									selected={selectedDate}
									onSelect={setSelectedDate}
									modifiersClassNames={{
										selected: "bg-blue-500 text-white",
									}}
								/>
							</div>

							{/* Heatmap display */}
							<div className="flex-1">
								{selectedDate && (
									<div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
										<h3 className="text-lg font-semibold mb-4 text-gray-800">
											{format(selectedDate, "MMMM d, yyyy")}
										</h3>

										{loading && (
											<div className="flex items-center justify-center h-64">
												<div className="text-gray-500">Loading...</div>
											</div>
										)}

										{error && (
											<div className="flex items-center justify-center h-64">
												<div className="text-red-500">{error}</div>
											</div>
										)}

										{heatmapUrl && !loading && !error && (
											<div className="relative">
												<img
													src={heatmapUrl}
													alt="Heatmap"
													className="w-full rounded-lg"
												/>
											</div>
										)}
									</div>
								)}

								{!selectedDate && (
									<div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 text-center text-gray-500">
										Select a date to view heatmap
									</div>
								)}
							</div>
						</div>
					</div>
				) : (
					<div className="flex items-center justify-center h-full">
						<div className="text-gray-500 text-lg">Select a camera</div>
					</div>
				)}
			</div>
		</div>
	);
}
