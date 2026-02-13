/**
 * ClipFlow AI — API Client
 * 封裝所有後端 API 呼叫
 */

const API_BASE = 'http://localhost:8000';

// ─── 通用 fetch 封裝 ─────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...options,
	});
	if (!res.ok) {
		const detail = await res.text();
		throw new Error(`API 錯誤 (${res.status}): ${detail}`);
	}
	return res.json();
}

// ─── 型別定義 ────────────────────────────────────────────

export interface ProjectSettings {
	mode: 'backtrack' | 'interval';
	language: string;
	model_size: string;
	ng_keywords: string[];
	ok_keywords: string[];
	start_keywords: string[];
	end_keywords: string[];
	pre_buffer: number;
	post_buffer: number;
	silence_threshold_db: number;
	silence_min_duration: number;
}

export interface Project {
	id: string;
	name: string;
	created_at: string;
	status: string;
	source_file: string | null;
	source_filename: string | null;
	duration_seconds: number | null;
	settings: ProjectSettings;
	error_message: string | null;
	progress: number;
}

export interface TranscriptWord {
	word: string;
	start: number;
	end: number;
	confidence: number;
}

export interface TranscriptSegment {
	text: string;
	start: number;
	end: number;
	words: TranscriptWord[];
}

export interface Marker {
	type: 'NG' | 'OK' | 'START' | 'END';
	word: string;
	start: number;
	end: number;
	confidence: number;
}

export interface Segment {
	id: string;
	type: string;
	start: number;
	end: number;
	trigger_marker: Marker | null;
	enabled: boolean;
	manual_adjusted: boolean;
}

export interface AnalysisStatus {
	status: string;
	progress: number;
	error_message: string | null;
}

// ─── 專案 API ────────────────────────────────────────────

export async function createProject(name: string): Promise<Project> {
	return apiFetch('/api/projects', {
		method: 'POST',
		body: JSON.stringify({ name }),
	});
}

export async function listProjects(): Promise<Project[]> {
	return apiFetch('/api/projects');
}

export async function getProject(id: string): Promise<Project> {
	return apiFetch(`/api/projects/${id}`);
}

export async function deleteProject(id: string): Promise<void> {
	await apiFetch(`/api/projects/${id}`, { method: 'DELETE' });
}

// ─── 上傳 & 分析 ─────────────────────────────────────────

export async function uploadVideo(projectId: string, file: File): Promise<void> {
	const form = new FormData();
	form.append('file', file);

	const res = await fetch(`${API_BASE}/api/projects/${projectId}/upload`, {
		method: 'POST',
		body: form,
	});
	if (!res.ok) {
		const detail = await res.text();
		throw new Error(`上傳失敗 (${res.status}): ${detail}`);
	}
}

export async function analyzeProject(projectId: string): Promise<void> {
	await apiFetch(`/api/projects/${projectId}/analyze`, { method: 'POST' });
}

export async function getAnalysisStatus(projectId: string): Promise<AnalysisStatus> {
	return apiFetch(`/api/projects/${projectId}/status`);
}

// ─── 逐字稿 ──────────────────────────────────────────────

export async function getTranscript(projectId: string): Promise<TranscriptSegment[]> {
	return apiFetch(`/api/projects/${projectId}/transcript`);
}

// ─── 片段 ────────────────────────────────────────────────

export async function getSegments(projectId: string): Promise<Segment[]> {
	return apiFetch(`/api/projects/${projectId}/segments`);
}

export async function updateSegment(
	projectId: string,
	segmentId: string,
	data: { start?: number; end?: number }
): Promise<Segment> {
	return apiFetch(`/api/projects/${projectId}/segments/${segmentId}`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function toggleSegment(projectId: string, segmentId: string): Promise<Segment> {
	return apiFetch(`/api/projects/${projectId}/segments/${segmentId}/toggle`, {
		method: 'PUT',
	});
}

// ─── 匯出 ────────────────────────────────────────────────

export function getExportUrl(projectId: string, format: 'edl' | 'xml' | 'srt' | 'video'): string {
	return `${API_BASE}/api/projects/${projectId}/export/${format}`;
}

export async function exportFile(
	projectId: string,
	format: 'edl' | 'xml' | 'srt' | 'video'
): Promise<Blob> {
	const res = await fetch(getExportUrl(projectId, format), {
		method: 'POST',
	});
	if (!res.ok) throw new Error(`匯出失敗 (${res.status})`);
	return res.blob();
}
