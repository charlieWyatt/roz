import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
	title: "Roz Heatmap Analytics",
	description: "Surveillance video heatmap viewer",
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="en">
			<body>{children}</body>
		</html>
	);
}
