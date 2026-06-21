"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { DocumentSummary, listDocuments, uploadDocument } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  reviewed: "bg-blue-100 text-blue-800",
  extracted: "bg-amber-100 text-amber-800",
  processing: "bg-gray-100 text-gray-700",
  failed: "bg-red-100 text-red-800",
  uploaded: "bg-gray-100 text-gray-700",
};

export default function Home() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      setBusy(true);
      setError(null);
      try {
        for (const file of Array.from(files)) {
          await uploadDocument(file);
        }
        await refresh();
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">LedgerLens</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload an invoice → extract fields with confidence → review &amp;
          correct → approve → export.
        </p>
      </header>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
          dragOver
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
      >
        <input
          type="file"
          className="hidden"
          accept="image/*,application/pdf"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
        />
        <span className="text-sm font-medium text-gray-700">
          {busy ? "Processing…" : "Drop a PDF or image here, or click to upload"}
        </span>
        <span className="mt-1 text-xs text-gray-400">
          Synthetic samples live in <code>backend/samples/</code>
        </span>
      </label>

      {error && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <section className="mt-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Documents
        </h2>
        {docs.length === 0 ? (
          <p className="text-sm text-gray-400">No documents yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {docs.map((d) => (
              <li key={d.id}>
                <Link
                  href={`/review/${d.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {d.filename}
                    </p>
                    <p className="text-xs text-gray-400">
                      #{d.id} · {new Date(d.created_at).toLocaleString()}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      STATUS_STYLES[d.status] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {d.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
