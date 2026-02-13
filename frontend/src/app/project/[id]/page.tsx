'use client';

import { useState, useEffect, useCallback, use } from 'react';
import {
	getProject,
	getTranscript,
	getSegments,
	toggleSegment,
	updateSegment,
	exportFile,
	getExportUrl,
	type Project,
	type TranscriptSegment,
	type Segment,
} from '@/lib/api';
import { formatTimePrecise } from '@/lib/utils';
import styles from './page.module.css';

// ─── 型別 ────────────────────────────────────────────────

type ExportFormat = 'edl' | 'xml' | 'srt' | 'video';

// ─── 主元件 ──────────────────────────────────────────────

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
	const { id } = use(params);

	const [project, setProject] = useState<Project | null>(null);
	const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
	const [segments, setSegments] = useState<Segment[]>([]);
	const [activeTab, setActiveTab] = useState<'timeline' | 'transcript'>('timeline');
	const [exporting, setExporting] = useState<string | null>(null);
	const [error, setError] = useState('');

	const load = useCallback(async () => {
		try {
			const [p, t, s] = await Promise.all([getProject(id), getTranscript(id), getSegments(id)]);
			setProject(p);
			setTranscript(t);
			setSegments(s);
		} catch {
			setError('載入專案失敗');
		}
	}, [id]);

	useEffect(() => {
		load();
	}, [load]);

	// ─── 匯出 ──────────────────────────────────────────────

	const handleExport = async (format: ExportFormat) => {
		setExporting(format);
		try {
			if (format === 'video') {
				// 影片直接開新視窗下載
				window.open(getExportUrl(id, 'video'), '_blank');
			} else {
				const blob = await exportFile(id, format);
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `${project?.name || 'export'}.${format}`;
				a.click();
				URL.revokeObjectURL(url);
			}
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : '匯出失敗');
		} finally {
			setExporting(null);
		}
	};

	// ─── 片段操作 ──────────────────────────────────────────

	const handleToggle = async (segId: string) => {
		try {
			const updated = await toggleSegment(id, segId);
			setSegments((prev) => prev.map((s) => (s.id === segId ? updated : s)));
		} catch {
			setError('切換失敗');
		}
	};

	const handleTimeEdit = async (segId: string, field: 'start' | 'end', value: number) => {
		try {
			const updated = await updateSegment(id, segId, { [field]: value });
			setSegments((prev) => prev.map((s) => (s.id === segId ? updated : s)));
		} catch {
			setError('更新時間點失敗');
		}
	};

	// ─── Loading ───────────────────────────────────────────

	if (!project) {
		return (
			<div className={styles.loadingScreen}>
				<span className='spinner' />
				<p>載入中⋯</p>
			</div>
		);
	}

	const enabledCount = segments.filter((s) => s.enabled).length;
	const totalDuration = segments
		.filter((s) => s.enabled)
		.reduce((acc, s) => acc + (s.end - s.start), 0);

	// ─── Render ────────────────────────────────────────────

	return (
		<div className={styles.workspace}>
			{/* ── Sidebar ─────────────────── */}
			<aside className={styles.sidebar}>
				<a href='/' className={styles.backLink}>
					← 返回首頁
				</a>

				<div className={styles.projectInfo}>
					<h2>{project.name}</h2>
					{project.source_filename && (
						<p className='text-secondary' style={{ fontSize: '0.8rem' }}>
							📎 {project.source_filename}
						</p>
					)}
				</div>

				<div className={styles.stats}>
					<div className={styles.statItem}>
						<span className={styles.statValue}>{segments.length}</span>
						<span className='text-muted'>片段總數</span>
					</div>
					<div className={styles.statItem}>
						<span className={styles.statValue}>{enabledCount}</span>
						<span className='text-muted'>啟用片段</span>
					</div>
					<div className={styles.statItem}>
						<span className={styles.statValue}>{formatTimePrecise(totalDuration)}</span>
						<span className='text-muted'>預估長度</span>
					</div>
				</div>

				<div className={styles.exportSection}>
					<h3>📤 匯出</h3>
					<div className={styles.exportButtons}>
						{(['edl', 'xml', 'srt', 'video'] as ExportFormat[]).map((fmt) => (
							<button
								key={fmt}
								className='btn btn-ghost btn-sm'
								disabled={exporting !== null}
								onClick={() => handleExport(fmt)}
							>
								{exporting === fmt ? <span className='spinner' /> : fmt.toUpperCase()}
							</button>
						))}
					</div>
				</div>
			</aside>

			{/* ── Main Content ────────────── */}
			<main className={styles.main}>
				{/* 錯誤 */}
				{error && (
					<div
						className={styles.error}
						style={{
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'center',
						}}
					>
						<span>{error}</span>
						<button
							onClick={() => setError('')}
							style={{
								background: 'none',
								border: 'none',
								color: 'var(--accent-red)',
								cursor: 'pointer',
							}}
						>
							✕
						</button>
					</div>
				)}

				{/* 頁籤 */}
				<div className={styles.tabs}>
					<button
						className={`${styles.tab} ${activeTab === 'timeline' ? styles.tabActive : ''}`}
						onClick={() => setActiveTab('timeline')}
					>
						🎬 時間軸片段
					</button>
					<button
						className={`${styles.tab} ${activeTab === 'transcript' ? styles.tabActive : ''}`}
						onClick={() => setActiveTab('transcript')}
					>
						📝 完整逐字稿
					</button>
				</div>

				{/* ── Tab: Timeline ────────── */}
				{activeTab === 'timeline' && (
					<div className={styles.segmentList}>
						{segments.length === 0 && (
							<p className='text-muted' style={{ textAlign: 'center', padding: 40 }}>
								尚無片段資料
							</p>
						)}
						{segments.map((seg, i) => (
							<div
								key={seg.id}
								className={`${styles.segmentCard} ${!seg.enabled ? styles.segmentDisabled : ''}`}
							>
								<div className={styles.segmentIndex}>
									<input
										type='checkbox'
										checked={seg.enabled}
										onChange={() => handleToggle(seg.id)}
										className={styles.checkbox}
									/>
									<span className='text-muted'>#{i + 1}</span>
								</div>

								<div className={styles.segmentBody}>
									<div className={styles.segmentTimes}>
										<TimeInput
											value={seg.start}
											onChange={(v) => handleTimeEdit(seg.id, 'start', v)}
										/>
										<span className='text-muted'>→</span>
										<TimeInput value={seg.end} onChange={(v) => handleTimeEdit(seg.id, 'end', v)} />
										<span className={`badge badge-blue`}>
											{formatTimePrecise(seg.end - seg.start)}
										</span>
									</div>

									{seg.trigger_marker && (
										<span
											className={`badge ${seg.trigger_marker.type === 'OK' || seg.trigger_marker.type === 'END' ? 'badge-green' : 'badge-red'}`}
										>
											{seg.trigger_marker.type}: &quot;{seg.trigger_marker.word}&quot;
										</span>
									)}
								</div>
							</div>
						))}
					</div>
				)}

				{/* ── Tab: Transcript ──────── */}
				{activeTab === 'transcript' && (
					<div className={styles.transcriptView}>
						{transcript.length === 0 && (
							<p className='text-muted' style={{ textAlign: 'center', padding: 40 }}>
								尚無逐字稿
							</p>
						)}
						{transcript.map((seg, i) => (
							<div key={i} className={styles.transcriptBlock}>
								<span className={styles.transcriptTime}>{formatTimePrecise(seg.start)}</span>
								<p>{seg.text}</p>
							</div>
						))}
					</div>
				)}
			</main>
		</div>
	);
}

// ─── 時間輸入子元件 ──────────────────────────────────────

function TimeInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
	const [editing, setEditing] = useState(false);
	const [text, setText] = useState(formatTimePrecise(value));

	useEffect(() => {
		if (!editing) setText(formatTimePrecise(value));
	}, [value, editing]);

	const commit = () => {
		setEditing(false);
		// 解析 mm:ss.cc
		const parts = text.split(':');
		if (parts.length === 2) {
			const min = parseInt(parts[0], 10) || 0;
			const secParts = parts[1].split('.');
			const sec = parseInt(secParts[0], 10) || 0;
			const cs = secParts[1] ? parseInt(secParts[1], 10) / 100 : 0;
			onChange(min * 60 + sec + cs);
		}
	};

	if (!editing) {
		return (
			<button className={styles.timeBtn} onClick={() => setEditing(true)} title='點擊編輯'>
				{formatTimePrecise(value)}
			</button>
		);
	}

	return (
		<input
			className={styles.timeInput}
			value={text}
			onChange={(e) => setText(e.target.value)}
			onBlur={commit}
			onKeyDown={(e) => e.key === 'Enter' && commit()}
			autoFocus
		/>
	);
}
