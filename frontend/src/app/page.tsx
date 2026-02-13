'use client';

import { useState, useEffect, useCallback } from 'react';
import {
	listProjects,
	createProject,
	deleteProject,
	uploadVideo,
	analyzeProject,
	type Project,
} from '@/lib/api';
import styles from './page.module.css';

export default function HomePage() {
	const [projects, setProjects] = useState<Project[]>([]);
	const [newName, setNewName] = useState('');
	const [creating, setCreating] = useState(false);
	const [error, setError] = useState('');

	const refresh = useCallback(async () => {
		try {
			const list = await listProjects();
			setProjects(list);
		} catch {
			setError('無法連線後端，請確認後端已啟動 (localhost:8000)');
		}
	}, []);

	useEffect(() => {
		refresh();
	}, [refresh]);

	const handleCreate = async () => {
		if (!newName.trim()) return;
		setCreating(true);
		try {
			await createProject(newName.trim());
			setNewName('');
			await refresh();
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : '建立失敗');
		} finally {
			setCreating(false);
		}
	};

	const handleDelete = async (id: string) => {
		if (!confirm('確定刪除此專案？')) return;
		try {
			await deleteProject(id);
			await refresh();
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : '刪除失敗');
		}
	};

	const handleUpload = async (projectId: string) => {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.mp4,.mov,.mkv,.avi,.webm,.mts';
		input.onchange = async () => {
			const file = input.files?.[0];
			if (!file) return;
			try {
				await uploadVideo(projectId, file);
				await analyzeProject(projectId);
				await refresh();
			} catch (e: unknown) {
				setError(e instanceof Error ? e.message : '上傳失敗');
			}
		};
		input.click();
	};

	const statusLabel = (status: string) => {
		const map: Record<string, { text: string; cls: string }> = {
			created: { text: '待上傳', cls: 'badge-yellow' },
			uploaded: { text: '待分析', cls: 'badge-blue' },
			analyzing: { text: '分析中', cls: 'badge-blue' },
			analyzed: { text: '已完成', cls: 'badge-green' },
			error: { text: '錯誤', cls: 'badge-red' },
		};
		return map[status] || { text: status, cls: '' };
	};

	return (
		<div className={styles.container}>
			{/* Header */}
			<header className={styles.header}>
				<div className={styles.logo}>
					<span className={styles.logoIcon}>✂️</span>
					<h1>ClipFlow AI</h1>
				</div>
				<p className={styles.tagline}>語音標記自動粗剪 — 從錄製到剪輯，一鍵完成</p>
			</header>

			{/* 錯誤提示 */}
			{error && (
				<div className={styles.error}>
					<span>{error}</span>
					<button onClick={() => setError('')} className={styles.errorClose}>
						✕
					</button>
				</div>
			)}

			{/* 新建專案 */}
			<div className={styles.createSection}>
				<input
					className='input'
					placeholder='輸入專案名稱（例如：EP.12 開箱影片）'
					value={newName}
					onChange={(e) => setNewName(e.target.value)}
					onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
				/>
				<button
					className='btn btn-primary'
					onClick={handleCreate}
					disabled={creating || !newName.trim()}
				>
					{creating ? <span className='spinner' /> : '＋ 新建專案'}
				</button>
			</div>

			{/* 專案列表 */}
			<div className={styles.grid}>
				{projects.length === 0 && (
					<div className={styles.empty}>
						<p className={styles.emptyIcon}>📁</p>
						<p>尚無專案</p>
						<p className='text-secondary'>建立你的第一個專案開始使用</p>
					</div>
				)}

				{projects.map((p, i) => {
					const st = statusLabel(p.status);
					return (
						<div
							key={p.id}
							className={`card ${styles.card} animate-fade-in`}
							style={{ animationDelay: `${i * 60}ms` }}
						>
							<div className={styles.cardHeader}>
								<h3>{p.name}</h3>
								<span className={`badge ${st.cls}`}>{st.text}</span>
							</div>

							{p.status === 'analyzing' && (
								<div style={{ marginBottom: 12 }}>
									<div className='progress-bar'>
										<div className='progress-bar-fill' style={{ width: `${p.progress * 100}%` }} />
									</div>
									<span className='text-muted' style={{ fontSize: '0.75rem' }}>
										{Math.round(p.progress * 100)}%
									</span>
								</div>
							)}

							<div className='text-secondary' style={{ fontSize: '0.8rem' }}>
								{p.source_filename && <p>📎 {p.source_filename}</p>}
								{p.duration_seconds && (
									<p>
										⏱️ {Math.floor(p.duration_seconds / 60)}:
										{String(Math.floor(p.duration_seconds % 60)).padStart(2, '0')}
									</p>
								)}
								<p>📅 {new Date(p.created_at).toLocaleDateString('zh-TW')}</p>
							</div>

							{p.error_message && <p className={styles.errorText}>❌ {p.error_message}</p>}

							<div className={styles.cardActions}>
								{p.status === 'created' && (
									<button className='btn btn-primary btn-sm' onClick={() => handleUpload(p.id)}>
										📤 上傳影片
									</button>
								)}
								{p.status === 'uploaded' && (
									<button
										className='btn btn-success btn-sm'
										onClick={async () => {
											await analyzeProject(p.id);
											await refresh();
										}}
									>
										🧠 開始分析
									</button>
								)}
								{p.status === 'analyzed' && (
									<a href={`/project/${p.id}`}>
										<button className='btn btn-primary btn-sm'>✏️ 開啟工作區</button>
									</a>
								)}
								<button className='btn btn-ghost btn-sm' onClick={() => handleDelete(p.id)}>
									🗑️
								</button>
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
}
