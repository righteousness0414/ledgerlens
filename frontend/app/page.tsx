"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { DocumentSummary, listDocuments, uploadDocument } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  approved: "border-green-200 bg-green-50 text-green-700",
  reviewed: "border-blue-200 bg-blue-50 text-blue-700",
  extracted: "border-amber-200 bg-amber-50 text-amber-700",
  processing: "border-gray-200 bg-gray-50 text-gray-600",
  failed: "border-red-200 bg-red-50 text-red-700",
  uploaded: "border-gray-200 bg-gray-50 text-gray-600",
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
        <h1 className="text-2xl font-semibold tracking-tight">LedgerLens</h1>
        <p className="mt-1 text-sm text-muted-foreground">
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
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition",
          dragOver
            ? "border-primary/50 bg-accent"
            : "border-border bg-card hover:border-muted-foreground/40",
        )}
      >
        <input
          type="file"
          className="hidden"
          accept="image/*,application/pdf"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
        />
        <span className="text-sm font-medium">
          {busy ? "Processing…" : "Drop a PDF or image here, or click to upload"}
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          Synthetic samples live in <code>backend/samples/</code>
        </span>
      </label>

      {error && (
        <p className="mt-4 rounded-md border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      <section className="mt-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Documents
        </h2>
        {docs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No documents yet.</p>
        ) : (
          <Card className="p-0">
            <CardContent className="divide-y p-0">
              {docs.map((d) => (
                <Link
                  key={d.id}
                  href={`/review/${d.id}`}
                  className="flex items-center justify-between px-4 py-3 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
                >
                  <div>
                    <p className="text-sm font-medium">{d.filename}</p>
                    <p className="text-xs text-muted-foreground">
                      #{d.id} · {new Date(d.created_at).toLocaleString()}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(STATUS_STYLES[d.status] ?? STATUS_STYLES.uploaded)}
                  >
                    {d.status}
                  </Badge>
                </Link>
              ))}
            </CardContent>
          </Card>
        )}
      </section>
    </main>
  );
}
