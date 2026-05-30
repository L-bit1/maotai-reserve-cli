import axios, { type AxiosError } from "axios";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";

export interface ApiResult<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export const apiBase = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const http = axios.create({
  baseURL: apiBase,
  timeout: 120000,
});

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => {
    const body = res.data as ApiResult;
    if (body && typeof body.code === "number" && body.code !== 0) {
      ElMessage.error(body.message || "请求失败");
      return Promise.reject(body);
    }
    return res;
  },
  (err: AxiosError<ApiResult & { detail?: ApiResult | string }>) => {
    const data = err.response?.data;
    let msg =
      data?.message ||
      (typeof data?.detail === "object" && data.detail !== null
        ? (data.detail as ApiResult).message
        : undefined) ||
      (typeof data?.detail === "string" ? data.detail : undefined) ||
      err.message ||
      "网络错误";

    if (!err.response) {
      msg =
        "无法连接管理后端。请先启动 API：在项目目录执行 ./scripts/start-api.sh（或双击「启动Web+API.command」）";
    } else if (err.response.status === 500 && msg.includes("status code 500")) {
      msg =
        "后端返回 500。请确认已运行 start-api.sh，并查看终端里的报错；也可打开 http://127.0.0.1:8000/docs 测试";
    }

    if (err.response?.status === 401) {
      useAuthStore().logout();
    }
    ElMessage.error(msg);
    return Promise.reject(data || err);
  }
);

export async function apiGet<T>(url: string, params?: object): Promise<T> {
  const { data } = await http.get<ApiResult<T>>(url, { params });
  return data.data as T;
}

export async function apiPost<T>(url: string, body?: object): Promise<T> {
  const { data } = await http.post<ApiResult<T>>(url, body);
  return data.data as T;
}

export async function apiPut<T>(url: string, body?: object): Promise<T> {
  const { data } = await http.put<ApiResult<T>>(url, body);
  return data.data as T;
}

export async function apiDelete<T>(url: string): Promise<T> {
  const { data } = await http.delete<ApiResult<T>>(url);
  return data.data as T;
}

export default http;
