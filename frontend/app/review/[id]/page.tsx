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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

function confidenceClass(c: number): string {
  if (c >= 0.85) return "border-green-200 bg-green-50 text-green-700";
  if (c >= 0.5) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-red-200 bg-red-50 text-red-700";
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
    <Card
      className={cn(
        "gap-0 p-3",
        field.flagged && "border-red-300 bg-red-50/40",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {field.key.replace(/_/g, " ")}
        </span>
        <Badge
          variant="outline"
          className={cn("font-semibold", confidenceClass(field.final_confidence))}
          title={`model ${field.model_confidence.toFixed(
            2,
          )} · validation ${field.validation_status}`}
        >
          {(field.final_confidence * 100).toFixed(0)}%
        </Badge>
      </div>

      <div className="mt-2">
        {editing ? (
          <div className="flex gap-2">
            <Input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && save()}
              className="h-8 flex-1"
            />
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? "…" : "Save"}
            </Button>
          </div>
        ) : (
          <button
            onClick={() => {
              setValue(field.effective_value ?? "");
              setEditing(true);
            }}
            className="w-full rounded px-2 py-1 text-left text-sm hover:bg-muted"
          >
            {field.effective_value || (
              <span className="text-muted-foreground">— (click to set)</span>
            )}
          </button>
        )}
      </div>

      {field.validation_message && field.validation_status === "fail" && (
        <p className="mt-1 text-xs text-destructive">
          ⚠ {field.validation_message}
        </p>
      )}
      {field.corrected_value !== null && (
        <p className="mt-1 text-xs text-blue-600">
          corrected by {field.corrected_by}
        </p>
      )}
    </Card>
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
      <main className="mx-auto max-w-3xl p-10 text-sm text-destructive">
        {error}
      </main>
    );
  if (!doc)
    return (
      <main className="mx-auto max-w-3xl p-10 text-muted-foreground">
        Loading…
      </main>
    );

  const isImage = doc.mime_type.startsWith("image/");

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-primary hover:underline">
            ← Documents
          </Link>
          <h1 className="mt-1 text-xl font-semibold tracking-tight">
            {doc.filename}
          </h1>
          <p className="text-xs text-muted-foreground">
            #{doc.id} · {doc.provider}/{doc.model} · status {doc.status} ·{" "}
            {doc.flagged_count} flagged
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            render={<a href={exportUrl(doc.id, "csv")} />}
          >
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            render={<a href={exportUrl(doc.id, "xlsx")} />}
          >
            Export Excel
          </Button>
          <Button
            onClick={approve}
            disabled={doc.status === "approved"}
            className="bg-green-600 text-white hover:bg-green-700"
          >
            {doc.status === "approved" ? "Approved ✓" : "Approve"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left: original document */}
        <Card className="bg-muted/40 p-2">
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
        </Card>

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
            <Card className="gap-0 p-3">
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Line items
              </h3>
              <Table>
                <TableBody>
                  {doc.line_items.map((li) => (
                    <TableRow key={li.id}>
                      <TableCell>{li.description}</TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {li.qty ?? ""}
                      </TableCell>
                      <TableCell className="text-right">
                        {li.amount?.toFixed(2) ?? ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </div>
      </div>
    </main>
  );
}
