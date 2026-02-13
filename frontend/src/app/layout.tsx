import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
	title: 'ClipFlow AI — 語音標記自動粗剪',
	description: '創作者的 A-roll 自動助理，將語音標籤轉化為剪輯軟體的時間軸',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang='zh-TW'>
			<body>{children}</body>
		</html>
	);
}
