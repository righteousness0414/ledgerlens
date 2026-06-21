// Thin client for the LedgerLens FastAPI backend.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface FieldOut {
  id: number;
  key: string;
  value: string | null;
  model_confidence: number;
  validation_status: "pass" | "fail" | "n/a";
  validation_message: string | null;
  final_confidence: number;
  flagged: boolean;
  corrected_value: string | null;
  corrected_by: string | null;
  corrected_at: string | null;
  effective_value: string | null;
}

export interface LineItemOut {
  id: number;
  description: string | null;
  qty: number | null;
  unit_price: number | null;
  amount: number | null;
  confidence: number;
}

export interface DocumentSummary {
  id: number;
  filename: string;
  mime_type: string;
  status: string;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  provider: string | null;
  model: string | null;
  fields: FieldOut[];
  line_items: LineItemOut[];
  flagged_count: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  return json(await fetch(`${API_BASE}/documents`, { cache: "no-store" }));
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  return json(await fetch(`${API_BASE}/documents/${id}`, { cache: "no-store" }));
}

export async function uploadDocument(file: File): Promise<DocumentDetail> {
  const form = new FormData();
  form.append("file", file);
  return json(
    await fetch(`${API_BASE}/documents`, { method: "POST", body: form }),
  );
}

export async function correctField(
  documentId: number,
  fieldId: number,
  value: string,
): Promise<FieldOut> {
  return json(
    await fetch(`${API_BASE}/documents/${documentId}/fields/${fieldId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value, actor: "reviewer" }),
    }),
  );
}

export async function approveDocument(id: number): Promise<DocumentDetail> {
  return json(
    await fetch(`${API_BASE}/documents/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "reviewer" }),
    }),
  );
}

export function exportUrl(id: number, format: "csv" | "xlsx"): string {
  return `${API_BASE}/documents/${id}/export?format=${format}`;
}
