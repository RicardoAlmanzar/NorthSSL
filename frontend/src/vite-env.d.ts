export {};

declare global {
	interface ImportMetaEnv {
		readonly VITE_NORTHSSL_API_URL?: string;
	}

	interface ImportMeta {
		readonly env: ImportMetaEnv;
	}
}
