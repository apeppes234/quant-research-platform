import { ExternalLinkIcon, FileTextIcon } from "lucide-react";
import type { ProvenanceCitation } from "../store/sessionStore";

type Props = {
  citation: ProvenanceCitation | null;
};

/**
 * Resolve an embeddable PDF URL for a citation:
 *  - a direct pdf_url (arXiv, or SSRN when a direct PDF is known) is embedded as-is;
 *  - a local_pdf_path is served through the sandboxed backend route (approved dirs only);
 *  - otherwise there is no PDF to show.
 */
export function pdfHrefFor(citation: ProvenanceCitation | null): string | null {
  if (!citation) return null;
  const arxivPdfUrl = arxivPdfUrlFor(citation);
  if (arxivPdfUrl) {
    return `/api/pdfs/arxiv?url=${encodeURIComponent(arxivPdfUrl)}`;
  }
  if (citation.pdfUrl && /^https?:\/\//i.test(citation.pdfUrl)) {
    return citation.pdfUrl;
  }
  if (citation.localPdfPath) {
    return `/api/pdfs?path=${encodeURIComponent(citation.localPdfPath)}`;
  }
  return null;
}

export function PaperPdfViewer({ citation }: Props) {
  const href = pdfHrefFor(citation);
  const sourcePage = citation?.sourceUrl || citation?.source;

  if (!citation) {
    return (
      <div className="pdf-viewer pdf-viewer--empty" data-testid="pdf-viewer">
        <FileTextIcon aria-hidden />
        <p>Select a source with a PDF to preview it here.</p>
      </div>
    );
  }

  if (!href) {
    return (
      <div className="pdf-viewer pdf-viewer--empty" data-testid="pdf-viewer">
        <FileTextIcon aria-hidden />
        <p>PDF not available.</p>
        {sourcePage && /^https?:\/\//i.test(sourcePage) ? (
          <a
            className="pdf-viewer__link"
            href={sourcePage}
            target="_blank"
            rel="noreferrer noopener"
          >
            <ExternalLinkIcon data-icon="inline-start" aria-hidden />
            Open source page instead
          </a>
        ) : null}
      </div>
    );
  }

  return (
    <div className="pdf-viewer" data-testid="pdf-viewer">
      <div className="pdf-viewer__bar">
        <span
          className="pdf-viewer__title"
          title={citation.title || citation.citation}
        >
          {citation.title || citation.citation || "PDF"}
        </span>
        <a
          className="pdf-viewer__link"
          href={href}
          target="_blank"
          rel="noreferrer noopener"
        >
          <ExternalLinkIcon data-icon="inline-start" aria-hidden />
          New tab
        </a>
        {sourcePage && /^https?:\/\//i.test(sourcePage) ? (
          <a
            className="pdf-viewer__link"
            href={sourcePage}
            target="_blank"
            rel="noreferrer noopener"
          >
            <ExternalLinkIcon data-icon="inline-start" aria-hidden />
            Source
          </a>
        ) : null}
      </div>
      <object
        className="pdf-viewer__frame"
        data={href}
        type="application/pdf"
        aria-label={`PDF preview: ${citation.title || citation.citation}`}
      >
        {/* Fallback for browsers that refuse to embed the object (e.g. cross-origin X-Frame-Options). */}
        <iframe
          className="pdf-viewer__frame"
          src={href}
          title={`PDF preview: ${citation.title || citation.citation}`}
        />
        <div className="pdf-viewer__fallback">
          <p>Your browser blocked the embedded preview.</p>
          <a href={href} target="_blank" rel="noreferrer noopener">
            Open the PDF in a new tab
          </a>
        </div>
      </object>
    </div>
  );
}

function arxivPdfUrlFor(citation: ProvenanceCitation): string | null {
  if (citation.provider !== "arxiv") return null;
  for (const value of [citation.pdfUrl, citation.sourceUrl, citation.source]) {
    const normalized = normalizeArxivPdfUrl(value);
    if (normalized) return normalized;
  }

  const arxivId =
    metadataString(citation.metadata?.arxiv_id) ||
    arxivIdFromText(citation.citation) ||
    arxivIdFromText(citation.source);
  return arxivId ? `https://arxiv.org/pdf/${arxivId}` : null;
}

function normalizeArxivPdfUrl(value: string | undefined): string | null {
  if (!value || !/^https?:\/\//i.test(value)) return null;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  if (!/(^|\.)arxiv\.org$/i.test(url.hostname)) return null;
  if (url.pathname.startsWith("/abs/")) {
    return `https://arxiv.org/pdf/${url.pathname.slice("/abs/".length)}`;
  }
  if (url.pathname.startsWith("/pdf/")) {
    return `https://arxiv.org${url.pathname}`;
  }
  return null;
}

function metadataString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function arxivIdFromText(value: string | undefined): string | null {
  if (!value) return null;
  const match = value.match(
    /(?:arxiv:\s*)?([a-z-]+(?:\.[A-Z]{2})?\/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?/i,
  );
  return match?.[0].replace(/^arxiv:\s*/i, "") ?? null;
}
