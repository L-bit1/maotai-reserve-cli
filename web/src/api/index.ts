import { apiGet, apiPost, apiPut, apiDelete } from "./http";

export const authApi = {
  login: (username: string, password: string) =>
    apiPost<{ access_token: string; expires_in: number }>("/auth/login", {
      username,
      password,
    }),
  me: () => apiGet<{ username: string }>("/auth/me"),
};

export const settingsApi = {
  get: () => apiGet<Record<string, unknown>>("/settings"),
  put: (body: Record<string, unknown>) => apiPut("/settings", body),
  health: () => apiGet<{ items: { level: string; category: string; message: string }[] }>("/settings/health"),
  scheduler: () =>
    apiGet<{ enabled: boolean; running: boolean; jobs: { id: string; next_run: string | null }[] }>(
      "/settings/scheduler"
    ),
};

export const accountsApi = {
  list: (page = 1, page_size = 20, search?: string) =>
    apiGet<{ total: number; items: AccountItem[] }>("/accounts", {
      page,
      page_size,
      ...(search ? { search } : {}),
    }),
  importCsv: async (file: File) => {
    const { apiBase } = await import("./http");
    const token = localStorage.getItem("mt_admin_token");
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${apiBase}/accounts/import-csv`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    const json = await res.json();
    if (json.code !== 0) throw new Error(json.message || "导入失败");
    return json.data as { created: number; updated: number; skipped: number };
  },
  syncCredentials: () => apiPost<{ synced: number }>("/accounts/sync-credentials"),
  create: (body: Partial<AccountItem>) => apiPost<AccountItem>("/accounts", body),
  update: (id: number, body: Partial<AccountItem>) => apiPut(`/accounts/${id}`, body),
  remove: (id: number) => apiDelete(`/accounts/${id}`),
  sendVcode: (id: number) => apiPost<{ message: string }>(`/accounts/${id}/send-vcode`),
  login: (id: number, vcode: string) =>
    apiPost<{ user_id: string; token_valid: boolean }>(`/accounts/${id}/login`, { vcode }),
  validate: (id: number) => apiPost<{ valid: boolean; message: string }>(`/accounts/${id}/validate-token`),
  status: (id: number) => apiGet<AccountStatus>(`/accounts/${id}/status`),
};

export const productsApi = {
  list: () => apiGet<ProductItem[]>("/products"),
  create: (body: ProductItem) => apiPost("/products", body),
  update: (id: number, body: ProductItem) => apiPut(`/products/${id}`, body),
  remove: (id: number) => apiDelete(`/products/${id}`),
};

export const shopsApi = {
  rank: (account_id: number, item_code: string, limit = 10) =>
    apiGet<{ session_id: string; items: ShopRankItem[] }>("/shops/rank", {
      account_id,
      item_code,
      limit,
    }),
  sync: (account_id: number) =>
    apiPost<{ provinces: number; shops: number }>(
      `/shops/sync?account_id=${account_id}`
    ),
};

export const jobsApi = {
  list: () => apiGet<JobItem[]>("/jobs"),
  create: (body: JobCreate) => apiPost<JobItem>("/jobs", body),
  get: (id: number) => apiGet<JobItem & { log_text?: string }>(`/jobs/${id}`),
  run: (id: number) => apiPost<{ message: string }>(`/jobs/${id}/run`),
  cancel: (id: number) => apiPost(`/jobs/${id}/cancel`),
  dryRun: (body: JobCreate) => apiPost<JobItem>("/jobs/dry-run", body),
};

export const recordsApi = {
  list: (params?: { page?: number; account_id?: number; status?: string }) =>
    apiGet<{ total: number; items: RecordItem[] }>("/records", params),
  stats: () => apiGet<StatsData>("/records/stats"),
};

export const lotteryApi = {
  results: (params?: { status?: string; payment_status?: string }) =>
    apiGet<{ total: number; items: LotteryRow[] }>("/lottery/results", params),
  sync: (today_only = true) =>
    apiPost<{ synced: number; errors: string[] }>(
      `/lottery/sync?today_only=${today_only}`
    ),
  weekendReserve: () => apiPost<{ message: string }>("/lottery/weekend-reserve"),
  travel: () => apiPost<{ message: string }>("/lottery/travel"),
};

export const paymentsApi = {
  pending: () =>
    apiGet<{ total: number; items: LotteryRow[]; notice: string }>("/payments/pending"),
  markPaid: (id: number) => apiPost(`/payments/${id}/mark-paid`),
  notify: () => apiPost<{ message: string; pending_count: number }>("/payments/notify"),
  exportBlob: async () => {
    const { apiBase } = await import("./http");
    const token = localStorage.getItem("mt_admin_token");
    const res = await fetch(`${apiBase}/payments/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.blob();
  },
};

export interface LotteryRow {
  id: number;
  mobile?: string;
  item_name?: string;
  session_name?: string;
  status?: string;
  payment_status?: string;
  order_id?: string;
  pay_deadline?: string;
}

export interface AccountItem {
  id?: number;
  mobile?: string;
  mobile_raw?: string;
  province?: string;
  city?: string;
  lat?: string;
  lng?: string;
  receiver_name?: string;
  enabled?: boolean;
  shop_strategy?: string;
  shop_id?: string;
  egress_group?: string;
  has_token?: boolean;
  remark?: string;
}

export interface AccountStatus {
  has_token: boolean;
  token_valid: boolean;
  message: string;
  last_error?: string;
}

export interface ProductItem {
  id?: number;
  item_code: string;
  name: string;
  enabled?: boolean;
  sort_order?: number;
}

export interface ShopRankItem {
  shop_id: string;
  name: string;
  inventory: number;
  city?: string;
}

export interface JobItem {
  id: number;
  name: string;
  type: string;
  status: string;
  dry_run: boolean;
  progress: number;
  log_preview?: string;
}

export interface JobCreate {
  name: string;
  type?: string;
  account_ids?: number[];
  product_ids?: number[];
  dry_run?: boolean;
  wait_until_reserve?: boolean;
}

export interface RecordItem {
  id: number;
  account_id: number;
  item_name: string;
  status: string;
  message: string;
  reserved_at: string;
}

export interface StatsData {
  total_attempts: number;
  submit_success: number;
  submit_success_rate: number;
}
