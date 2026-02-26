<script lang="ts">
	let file = $state<File | null>(null);
	let isDragging = $state(false);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let downloadUrl = $state<string | null>(null);

	// Use relative URL - nginx proxies /transform to the API
	const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : '/api';

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		
		const files = e.dataTransfer?.files;
		if (files && files.length > 0) {
			const droppedFile = files[0];
			if (droppedFile.name.endsWith('.zip')) {
				file = droppedFile;
				error = null;
				downloadUrl = null;
			} else {
				error = 'Please drop a .zip file';
			}
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			const selectedFile = input.files[0];
			if (selectedFile.name.endsWith('.zip')) {
				file = selectedFile;
				error = null;
				downloadUrl = null;
			} else {
				error = 'Please select a .zip file';
			}
		}
	}

	async function handleSubmit() {
		if (!file) return;
		
		isLoading = true;
		error = null;
		downloadUrl = null;

		try {
			const formData = new FormData();
			formData.append('zip_file', file);

			const response = await fetch(`${API_URL}/transform`, {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || 'Transform failed');
			}

			const blob = await response.blob();
			downloadUrl = URL.createObjectURL(blob);
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			isLoading = false;
		}
	}

	function handleDownload() {
		if (!downloadUrl || !file) return;
		
		const a = document.createElement('a');
		a.href = downloadUrl;
		a.download = `transformed_${file.name}`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
	}

	function handleReset() {
		file = null;
		downloadUrl = null;
		error = null;
	}
</script>

<svelte:head>
	<title>HSDS Transformer</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center p-8">
	<div class="max-w-xl w-full">
		<!-- Header -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-gray-900 mb-4">HSDS Transformer</h1>
			<p class="text-lg text-gray-600">
				Transform your CSV data into HSDS JSON format. 
				Drop a zip file containing your input CSVs and mapping files to get started.
			</p>
		</div>

		<!-- File Drop Zone -->
		<div
			class="bg-white rounded-lg shadow-sm border-2 border-dashed p-8 text-center transition-colors
				{isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}"
			role="button"
			tabindex="0"
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			ondrop={handleDrop}
			onclick={() => document.getElementById('fileInput')?.click()}
			onkeydown={(e) => e.key === 'Enter' && document.getElementById('fileInput')?.click()}
		>
			{#if file}
				<div class="flex items-center justify-center gap-3">
					<svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span class="text-gray-700 font-medium">{file.name}</span>
					<button 
						class="text-gray-400 hover:text-gray-600 ml-2"
						onclick={(e) => { e.stopPropagation(); handleReset(); }}
						aria-label="Remove file"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			{:else}
				<svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
				</svg>
				<p class="text-gray-600 mb-2">Drag and drop a .zip file here</p>
				<p class="text-gray-400 text-sm">or click to browse</p>
				<input 
					type="file" 
					id="fileInput" 
					accept=".zip" 
					class="hidden" 
					onchange={handleFileSelect}
				/>
			{/if}
		</div>

		<!-- Error Message -->
		{#if error}
			<div class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
				<p class="text-red-600 text-sm">{error}</p>
			</div>
		{/if}

		<!-- Download Button (Success) -->
		{#if downloadUrl}
			<div class="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
				<p class="text-green-700 text-sm mb-3">Transformation complete!</p>
				<button
					onclick={handleDownload}
					class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
					</svg>
					Download Transformed Files
				</button>
			</div>
		{/if}

		<!-- Submit Button -->
		{#if file && !downloadUrl}
			<button
				onclick={handleSubmit}
				disabled={isLoading}
				class="mt-4 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
			>
				{#if isLoading}
					<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Transforming...
				{:else}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
					Transform
				{/if}
			</button>
		{/if}
	</div>
</div>
