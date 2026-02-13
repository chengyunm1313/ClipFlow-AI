/**
 * 時間格式化工具
 */

/** 秒數 → mm:ss 格式 */
export function formatTime(seconds: number): string {
	const m = Math.floor(seconds / 60);
	const s = Math.floor(seconds % 60);
	return `${m}:${String(s).padStart(2, '0')}`;
}

/** 秒數 → mm:ss.ms 格式 */
export function formatTimePrecise(seconds: number): string {
	const m = Math.floor(seconds / 60);
	const s = Math.floor(seconds % 60);
	const ms = Math.floor((seconds % 1) * 100);
	return `${m}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

/** mm:ss 或 mm:ss.ms 格式 → 秒數 */
export function parseTime(str: string): number {
	const parts = str.split(':');
	if (parts.length !== 2) return 0;
	const min = parseInt(parts[0], 10) || 0;
	const secParts = parts[1].split('.');
	const sec = parseInt(secParts[0], 10) || 0;
	const ms = secParts[1] ? parseInt(secParts[1], 10) / 100 : 0;
	return min * 60 + sec + ms;
}
