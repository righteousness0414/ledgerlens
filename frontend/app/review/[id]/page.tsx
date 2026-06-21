"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  API_BASE,
  DocumentDetail,
  FieldOut,
  approveDocument,
  correctField,
  exportUrl,
  getDocument,
} from "@/lib/api";

function confidenceColor(c: number): string {
  if (c >= 0.85) return "text-green-700 bg-green-50";
  if (c >= 0.5) return "text-amber-700 bg-amber-50";
  return "text-red-700 bg-red-50";
}

function FieldRow({
  field,
  docId,
  onChange,
}: {
  field: FieldOut;
  docId: number;
  onChange: (f: FieldOut) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(field.effective_value ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await correctField(docId, field.id, value);
      onChange(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={`rounded-lg border p-3 ${
        field.flagged ? "border-red-300 bg-red-50/40" : "border-gray-200"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
          {field.key.replace(/_/g, " ")}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${confidenceColor(
            field.final_confidence,
          )}`}
          title={`model ${field.model_confidence.toFixed(
            2,
          )} · validation ${field.validation_status}`}
        >
          {(field.final_confidence * 100).toFixed(0)}%
        </span>
      </div>

      <div className="mt-2">
        {editing ? (
          <div className="flex gap-2">
            <input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && save()}
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
            />
            <button
              onClick={save}
              disabled={saving}
              className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "…" : "Save"}
            </button>
          </div>
        ) : (
          <button
            onClick={() => {
              setValue(field.effective_value ?? "");
              setEditing(true);
            }}
            className="w-full rounded px-2 py-1 text-left text-sm text-gray-900 hover:bg-gray-100"
          >
            {field.effective_value || (
              <span className="text-gray-400">— (click to set)</span>
            )}
          </button>
        )}
      </div>

      {field.validation_message && field.validation_status === "fail" && (
        <p className="mt-1 text-xs text-red-600">⚠ {field.validation_message}</p>
      )}
      {field.corrected_value !== null && (
        <p className="mt-1 text-xs text-blue-600">
          corrected by {field.corrected_by}
        </p>
      )}
    </div>
  );
}

export default function ReviewPage() {
  const params = useParams<{ id: string }>();
  const docId = Number(params.id);

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDoc(await getDocument(docId));
    } catch (e) {
      setError(String(e));
    }
  }, [docId]);

  useEffect(() => {
    load();
  }, [load]);

  const onFieldChange = useCallback((updated: FieldOut) => {
    setDoc((prev) =>
      prev
        ? {
            ...prev,
            fields: prev.fields.map((f) => (f.id === updated.id ? updated : f)),
            flagged_count: prev.fields
              .map((f) => (f.id === updated.id ? updated : f))
              .filter((f) => f.flagged).length,
          }
        : prev,
    );
  }, []);

  const approve = async () => {
    setDoc(await approveDocument(docId));
  };

  const previewUrl = useMemo(
    () => `${API_BASE}/documents/${docId}/file`,
    [docId],
  );

  if (error)
    return (
      <main className="mx-auto max-w-3xl p-10 text-sm text-red-700">
        {error}
      </main>
    );
  if (!doc)
    return <main className="mx-auto max-w-3xl p-10 text-gray-400">Loading…</main>;

  const isImage = doc.mime_type.startsWith("image/");

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            ← Documents
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-gray-900">
            {doc.filename}
          </h1>
          <p className="text-xs text-gray-400">
            #{doc.id} · {doc.provider}/{doc.model} · status {doc.status} ·{" "}
            {doc.flagged_count} flagged
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={exportUrl(doc.id, "csv")}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export CSV
          </a>
          <a
            href={exportUrl(doc.id, "xlsx")}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export Excel
          </a>
          <button
            onClick={approve}
            disabled={doc.status === "approved"}
            className="rounded bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {doc.status === "approved" ? "Approved ✓" : "Approve"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left: original document */}
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-2">
          {isImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewUrl}
              alt={doc.filename}
              className="mx-auto max-h-[70vh] w-auto rounded"
            />
          ) : (
            <iframe
              src={previewUrl}
              title={doc.filename}
              className="h-[70vh] w-full rounded"
            />
          )}
        </div>

        {/* Right: editable fields, flagged first */}
        <div className="space-y-3">
          {[...doc.fields]
            .sort((a, b) => Number(b.flagged) - Number(a.flagged))
            .map((field) => (
              <FieldRow
                key={field.id}
                field={field}
                docId={doc.id}
                onChange={onFieldChange}
              />
            ))}

          {doc.line_items.length > 0 && (
            <div className="rounded-lg border border-gray-200 p-3">
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                Line items
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {doc.line_items.map((li) => (
                    <tr key={li.id} className="border-t border-gray-100">
                      <td className="py-1 text-gray-700">{li.description}</td>
                      <td className="py-1 text-right text-gray-500">
                        {li.qty ?? ""}
                      </td>
                      <td className="py-1 text-right text-gray-900">
                        {li.amount?.toFixed(2) ?? ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
